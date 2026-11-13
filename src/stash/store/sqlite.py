import sqlite3
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta
from enum import StrEnum
from importlib.resources.abc import Traversable
from pathlib import Path

from stash.domain import (
    CaptureStatus,
    Item,
    ItemType,
    KeyDate,
    Nudge,
    NudgeKey,
    NudgeKind,
    Outcome,
    Person,
    RawCapture,
    Stage,
    Step,
    require_aware,
    utc_text,
)
from stash.store import _sql as sql
from stash.store._checks import require_date_range, require_instant_range, require_non_negative
from stash.store._connect import open_connection
from stash.store._item_writes import SqliteItemWrites
from stash.store._ledger import SqliteLedger
from stash.store._migrate import apply_migrations, packaged_migrations
from stash.store._people import SqlitePeople
from stash.store._rows import (
    capture_from_row,
    capture_values,
    item_from_row,
    outcome_from_row,
)
from stash.store._steps import SqliteSteps
from stash.store._transaction import immediate_transaction
from stash.store.port import DEFAULT_PAGE_SIZE, BackupError, UnknownCaptureError

_PRIMARY_KEY_VIOLATION = "SQLITE_CONSTRAINT_PRIMARYKEY"
BUSY_TIMEOUT = timedelta(seconds=5)


def _value_of(member: StrEnum | None) -> str | None:
    return None if member is None else member.value


class SqliteStore:
    def __init__(
        self,
        path: Path,
        migrations: Traversable | None = None,
        busy_timeout: timedelta = BUSY_TIMEOUT,
    ) -> None:
        # One connection serves all threads: a transaction holds this lock while it waits to begin.
        self._lock = threading.RLock()
        self._connection = open_connection(path, busy_timeout)
        try:
            self._item_writes = SqliteItemWrites(self._connection, self._lock)
            self._steps = SqliteSteps(self._connection, self._lock)
            self._people = SqlitePeople(self._connection, self._lock)
            self._ledger = SqliteLedger(self._connection, self._lock)
            apply_migrations(
                self._connection, packaged_migrations() if migrations is None else migrations
            )
        except BaseException:
            self._connection.close()
            raise

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
        self._item_writes.save_item(item)

    @contextmanager
    def writing(self) -> Iterator[None]:
        with self._lock, immediate_transaction(self._connection):
            yield

    def update_item(self, item: Item) -> None:
        self._item_writes.update_item(item)

    def group_item(self, child: Item) -> None:
        self._item_writes.group_item(child)

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM items WHERE id = ?", (item_id,)
            ).fetchone()
        return None if row is None else item_from_row(row)

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM items WHERE id = ?", (item_id,))

    def delete_item_if_untouched(self, item_id: str) -> bool:
        parameters = {"item_id": item_id, "done": Stage.DONE.value}
        with self._lock:
            return self._connection.execute(sql.DELETE_ITEM_IF_UNTOUCHED, parameters).rowcount > 0

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

    def items_dated_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        return self._items_from(
            sql.ITEMS_DATED_BETWEEN, {"start": start.isoformat(), "end": end.isoformat()}
        )

    def planned_awaiting_outcome_dated_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        parameters = {
            "planned": Stage.PLANNED.value,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        return self._items_from(sql.PLANNED_AWAITING_OUTCOME_DATED_BETWEEN, parameters)

    def want_to_older_than(self, cutoff: datetime, limit: int) -> list[Item]:
        return self._stage_older_than(Stage.WANT_TO, cutoff, limit)

    def doing_older_than(self, cutoff: datetime, limit: int) -> list[Item]:
        return self._stage_older_than(Stage.DOING, cutoff, limit)

    def created_between(self, start: datetime, end: datetime) -> list[Item]:
        require_instant_range(start, end)
        return self._items_from(
            sql.CREATED_BETWEEN, {"start": utc_text(start), "end": utc_text(end)}
        )

    def add_outcome(self, outcome: Outcome) -> None:
        self._item_writes.add_outcome(outcome)

    def save_outcome(self, outcome: Outcome) -> None:
        self._item_writes.save_outcome(outcome)

    def record_completion(self, item: Item, outcome: Outcome) -> None:
        self._item_writes.record_completion(item, outcome)

    def outcomes_for(self, item_id: str) -> list[Outcome]:
        with self._lock:
            rows = self._connection.execute(sql.OUTCOMES_FOR_ITEM, (item_id,)).fetchall()
        return [outcome_from_row(row) for row in rows]

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        with self._lock:
            row = self._connection.execute(sql.OUTCOME_BY_ID, (outcome_id,)).fetchone()
        return None if row is None else outcome_from_row(row)

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        self._steps.save_steps(item_id, steps)

    def steps_for(self, item_id: str) -> list[Step]:
        return self._steps.steps_for(item_id)

    def save_step(self, step: Step) -> None:
        self._steps.save_step(step)

    def get_step(self, step_id: str) -> Step | None:
        return self._steps.get_step(step_id)

    def open_confirmed_steps(self) -> list[Step]:
        return self._steps.open_confirmed_steps()

    def save_person(self, person: Person) -> None:
        self._people.save_person(person)

    def get_person(self, person_id: str) -> Person | None:
        return self._people.get_person(person_id)

    def delete_person(self, person_id: str) -> None:
        self._people.delete_person(person_id)

    def list_people(self) -> list[Person]:
        return self._people.list_people()

    def find_by_name(self, name: str) -> Person | None:
        return self._people.find_by_name(name)

    def save_key_date(self, key_date: KeyDate) -> None:
        self._people.save_key_date(key_date)

    def key_dates_for(self, person_id: str) -> list[KeyDate]:
        return self._people.key_dates_for(person_id)

    def key_dates_between(self, start: date, end: date) -> list[tuple[KeyDate, date]]:
        return self._people.key_dates_between(start, end)

    def link(self, item_id: str, person_id: str) -> None:
        self._people.link(item_id, person_id)

    def people_for(self, item_id: str) -> list[Person]:
        return self._people.people_for(item_id)

    def items_for(self, person_id: str, item_type: ItemType | None = None) -> list[Item]:
        return self._people.items_for(person_id, item_type)

    def items_naming_people(self) -> list[Item]:
        return self._people.items_naming_people()

    def was_sent(self, key: NudgeKey) -> bool:
        return self._ledger.was_sent(key)

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool:
        return self._ledger.record_all_sent(nudges, sent_at)

    def last_sent(self, kind: NudgeKind) -> datetime | None:
        return self._ledger.last_sent(kind)

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

    def _items_from(
        self, query: str, parameters: Mapping[str, object] | tuple[str, ...]
    ) -> list[Item]:
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
        return [item_from_row(row) for row in rows]

    def _stage_older_than(self, stage: Stage, cutoff: datetime, limit: int) -> list[Item]:
        require_aware("cutoff", cutoff)
        require_non_negative("limit", limit)
        parameters = {"stage": stage.value, "cutoff": utc_text(cutoff), "limit": limit}
        return self._items_from(sql.STAGE_OLDER_THAN, parameters)
