import sqlite3
import threading
import time
from collections.abc import Mapping
from contextlib import closing
from datetime import date
from enum import StrEnum
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import NoReturn

from stash.domain import CaptureStatus, Item, ItemType, Outcome, RawCapture, Stage
from stash.store import _sql as sql
from stash.store._migrate import apply_migrations, packaged_migrations
from stash.store._rows import (
    capture_from_row,
    capture_values,
    item_from_row,
    item_values,
    outcome_from_row,
    outcome_values,
)
from stash.store._transaction import immediate_transaction
from stash.store.port import (
    DEFAULT_PAGE_SIZE,
    BackupError,
    DuplicateOutcomeError,
    UnknownCaptureError,
    UnknownItemError,
    require_date_range,
    require_non_negative,
    require_outcome_for_item,
)

_PRIMARY_KEY_VIOLATION = "SQLITE_CONSTRAINT_PRIMARYKEY"
_FOREIGN_KEY_VIOLATION = "SQLITE_CONSTRAINT_FOREIGNKEY"
_BUSY = "SQLITE_BUSY"
_WAL_SWITCH_DEADLINE_SECONDS = 5.0
_WAL_SWITCH_RETRY_SECONDS = 0.01


def _value_of(member: StrEnum | None) -> str | None:
    return None if member is None else member.value


def _enable_wal(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal":
        return
    deadline = time.monotonic() + _WAL_SWITCH_DEADLINE_SECONDS
    while True:
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as error:
            if error.sqlite_errorname != _BUSY or time.monotonic() >= deadline:
                raise
            time.sleep(_WAL_SWITCH_RETRY_SECONDS)


class SqliteStore:
    def __init__(self, path: Path, migrations: Traversable | None = None) -> None:
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        try:
            self._configure()
            apply_migrations(
                self._connection, packaged_migrations() if migrations is None else migrations
            )
        except BaseException:
            self._connection.close()
            raise

    def _configure(self) -> None:
        self._connection.row_factory = sqlite3.Row
        _enable_wal(self._connection)
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.create_function("casefold", 1, str.casefold, deterministic=True)

    def add_capture(self, capture: RawCapture) -> bool:
        with self._lock:
            try:
                cursor = self._connection.execute(sql.INSERT_CAPTURE, capture_values(capture))
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorname != _PRIMARY_KEY_VIOLATION:
                    raise
                raise ValueError(f"capture id {capture.id!r} already exists") from error
            return cursor.rowcount == 1

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None:
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE captures SET status = ? WHERE id = ?", (status.value, capture_id)
            )
        if cursor.rowcount == 0:
            raise UnknownCaptureError(capture_id)

    def get_capture(self, capture_id: str) -> RawCapture | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM captures WHERE id = ?", (capture_id,)
            ).fetchone()
        return None if row is None else capture_from_row(row)

    def pending_captures(self) -> list[RawCapture]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM captures WHERE status = ? ORDER BY received_at, id",
                (CaptureStatus.PENDING.value,),
            ).fetchall()
        return [capture_from_row(row) for row in rows]

    def save_item(self, item: Item) -> None:
        with self._lock:
            try:
                self._connection.execute(sql.UPSERT_ITEM, item_values(item))
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorname != _FOREIGN_KEY_VIOLATION:
                    raise
                self._refuse_item(item, error)

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
        return None if row is None else item_from_row(row)

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM items WHERE id = ?", (item_id,))

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        require_non_negative("limit", limit)
        require_non_negative("offset", offset)
        parameters = {
            "stage": _value_of(stage),
            "item_type": _value_of(item_type),
            "limit": limit,
            "offset": offset,
        }
        return self._items_from(sql.LIST_ITEMS, parameters)

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        require_non_negative("limit", limit)
        if not query.strip():
            return []
        return self._items_from(sql.SEARCH_ITEMS, {"needle": query.casefold(), "limit": limit})

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        require_non_negative("limit", limit)
        require_non_negative("offset", offset)
        parameters = {
            "item_type": _value_of(item_type),
            "dropped": Stage.DROPPED.value,
            "limit": limit,
            "offset": offset,
        }
        return self._items_from(sql.LIBRARY, parameters)

    def children_of(self, parent_id: str) -> list[Item]:
        return self._items_from(sql.CHILDREN_OF, (parent_id,))

    def done_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        return self._items_from(
            sql.DONE_BETWEEN, {"start": start.isoformat(), "end": end.isoformat()}
        )

    def add_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            self._insert_outcome(outcome)

    def save_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            try:
                self._connection.execute(sql.UPSERT_OUTCOME, outcome_values(outcome))
            except sqlite3.IntegrityError as error:
                self._refuse_outcome(outcome, error)

    def record_completion(self, item: Item, outcome: Outcome) -> None:
        require_outcome_for_item(item, outcome)
        with self._lock, immediate_transaction(self._connection):
            if not self._exists(sql.ITEM_EXISTS, item.id):
                raise UnknownItemError(item.id)
            self.save_item(item)
            self._insert_outcome(outcome)

    def outcomes_for(self, item_id: str) -> list[Outcome]:
        with self._lock:
            rows = self._connection.execute(sql.OUTCOMES_FOR_ITEM, (item_id,)).fetchall()
        return [outcome_from_row(row) for row in rows]

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        with self._lock:
            row = self._connection.execute(sql.OUTCOME_BY_ID, (outcome_id,)).fetchone()
        return None if row is None else outcome_from_row(row)

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else row["value"]

    def put_setting(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(sql.UPSERT_SETTING, (key, value))

    def backup_to(self, target: Path) -> None:
        try:
            with self._lock, closing(sqlite3.connect(str(target))) as destination:
                self._connection.backup(destination)
        except sqlite3.Error as error:
            raise BackupError(str(error)) from error

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _refuse_item(self, item: Item, error: sqlite3.IntegrityError) -> NoReturn:
        if not self._exists(sql.CAPTURE_EXISTS, item.capture_id):
            raise UnknownCaptureError(item.capture_id) from error
        if item.parent_id is not None:
            raise UnknownItemError(item.parent_id) from error
        raise error

    def _items_from(
        self, query: str, parameters: Mapping[str, object] | tuple[str, ...]
    ) -> list[Item]:
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [item_from_row(row) for row in rows]

    def _exists(self, query: str, row_id: str) -> bool:
        return self._connection.execute(query, (row_id,)).fetchone() is not None

    def _insert_outcome(self, outcome: Outcome) -> None:
        try:
            self._connection.execute(sql.INSERT_OUTCOME, outcome_values(outcome))
        except sqlite3.IntegrityError as error:
            self._refuse_outcome(outcome, error)

    def _refuse_outcome(self, outcome: Outcome, error: sqlite3.IntegrityError) -> NoReturn:
        if error.sqlite_errorname == _PRIMARY_KEY_VIOLATION:
            raise DuplicateOutcomeError(outcome.id) from error
        if error.sqlite_errorname == _FOREIGN_KEY_VIOLATION:
            raise UnknownItemError(outcome.item_id) from error
        raise error
