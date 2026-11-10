import sqlite3
import threading
from collections.abc import Sequence

from stash.domain import Step
from stash.store import _sql as sql
from stash.store._checks import require_steps_for_item
from stash.store._rows import step_from_row, step_values
from stash.store._transaction import immediate_transaction
from stash.store.port import DuplicateStepError, UnknownItemError


class SqliteSteps:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        require_steps_for_item(item_id, steps)
        with self._lock, immediate_transaction(self._connection):
            self._require_item(item_id)
            self._connection.execute(sql.DELETE_STEPS_OF_ITEM, (item_id,))
            for step in steps:
                self._upsert(step)

    def steps_for(self, item_id: str) -> list[Step]:
        with self._lock:
            rows = self._connection.execute(sql.STEPS_FOR_ITEM, (item_id,)).fetchall()
        return [step_from_row(row) for row in rows]

    def save_step(self, step: Step) -> None:
        with self._lock, immediate_transaction(self._connection):
            self._require_item(step.item_id)
            self._upsert(step)

    def get_step(self, step_id: str) -> Step | None:
        with self._lock:
            row = self._connection.execute(sql.STEP_BY_ID, (step_id,)).fetchone()
        return None if row is None else step_from_row(row)

    def open_confirmed_steps(self) -> list[Step]:
        with self._lock:
            rows = self._connection.execute(sql.OPEN_CONFIRMED_STEPS).fetchall()
        return [step_from_row(row) for row in rows]

    def _require_item(self, item_id: str) -> None:
        if self._connection.execute(sql.ITEM_EXISTS, (item_id,)).fetchone() is None:
            raise UnknownItemError(item_id)

    def _upsert(self, step: Step) -> None:
        cursor = self._connection.execute(sql.UPSERT_STEP, step_values(step))
        if cursor.rowcount == 0:
            raise DuplicateStepError(step.id)
