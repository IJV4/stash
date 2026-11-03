import sqlite3
import threading
import time
from contextlib import closing
from importlib.resources.abc import Traversable
from pathlib import Path

from stash.domain import CaptureStatus, Item, ItemType, RawCapture, Stage
from stash.store._migrate import apply_migrations, packaged_migrations
from stash.store._rows import capture_from_row, capture_values, item_from_row, item_values
from stash.store.port import DEFAULT_PAGE_SIZE, UnknownCaptureError, require_non_negative

_PRIMARY_KEY_VIOLATION = "SQLITE_CONSTRAINT_PRIMARYKEY"
_FOREIGN_KEY_VIOLATION = "SQLITE_CONSTRAINT_FOREIGNKEY"
_BUSY = "SQLITE_BUSY"
_WAL_SWITCH_DEADLINE_SECONDS = 5.0
_WAL_SWITCH_RETRY_SECONDS = 0.01

_INSERT_CAPTURE = """
INSERT INTO captures (id, chat_id, message_id, received_at, text, media_paths, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (chat_id, message_id) DO NOTHING
"""

_UPSERT_ITEM = """
INSERT INTO items (id, capture_id, item_type, title, stage, source_url, note, details,
                   tags, people, date, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (id) DO UPDATE SET
    capture_id = excluded.capture_id,
    item_type = excluded.item_type,
    title = excluded.title,
    stage = excluded.stage,
    source_url = excluded.source_url,
    note = excluded.note,
    details = excluded.details,
    tags = excluded.tags,
    people = excluded.people,
    date = excluded.date,
    created_at = excluded.created_at,
    updated_at = excluded.updated_at
"""

_LIST_ITEMS = """
SELECT * FROM items
WHERE (:stage IS NULL OR stage = :stage) AND (:item_type IS NULL OR item_type = :item_type)
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset
"""

_SEARCH_ITEMS = """
SELECT * FROM items
WHERE instr(casefold(title), :needle) > 0
   OR instr(casefold(note), :needle) > 0
   OR EXISTS (SELECT 1 FROM json_each(items.tags) WHERE instr(casefold(value), :needle) > 0)
ORDER BY created_at DESC, id DESC
LIMIT :limit
"""

_UPSERT_SETTING = """
INSERT INTO settings (key, value) VALUES (?, ?)
ON CONFLICT (key) DO UPDATE SET value = excluded.value
"""


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
                cursor = self._connection.execute(_INSERT_CAPTURE, capture_values(capture))
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
                self._connection.execute(_UPSERT_ITEM, item_values(item))
            except sqlite3.IntegrityError as error:
                if error.sqlite_errorname != _FOREIGN_KEY_VIOLATION:
                    raise
                raise UnknownCaptureError(item.capture_id) from error

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
        with self._lock:
            rows = self._connection.execute(
                _LIST_ITEMS,
                {
                    "stage": None if stage is None else stage.value,
                    "item_type": None if item_type is None else item_type.value,
                    "limit": limit,
                    "offset": offset,
                },
            ).fetchall()
        return [item_from_row(row) for row in rows]

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        require_non_negative("limit", limit)
        if not query.strip():
            return []
        with self._lock:
            rows = self._connection.execute(
                _SEARCH_ITEMS, {"needle": query.casefold(), "limit": limit}
            ).fetchall()
        return [item_from_row(row) for row in rows]

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else row["value"]

    def put_setting(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(_UPSERT_SETTING, (key, value))

    def backup_to(self, target: Path) -> None:
        with self._lock, closing(sqlite3.connect(str(target))) as destination:
            self._connection.backup(destination)

    def close(self) -> None:
        with self._lock:
            self._connection.close()
