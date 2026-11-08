import sqlite3
import threading
from typing import NoReturn

from stash.domain import Item, Outcome
from stash.store import _sql as sql
from stash.store._rows import item_from_row, item_values, outcome_values
from stash.store._transaction import immediate_transaction
from stash.store.port import (
    ChildHoldsItemsError,
    DuplicateOutcomeError,
    ParentIsGroupedError,
    UnknownCaptureError,
    UnknownItemError,
    require_outcome_for_item,
    require_parent,
)

_PRIMARY_KEY_VIOLATION = "SQLITE_CONSTRAINT_PRIMARYKEY"
_FOREIGN_KEY_VIOLATION = "SQLITE_CONSTRAINT_FOREIGNKEY"


class SqliteItemWrites:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def save_item(self, item: Item) -> None:
        with self._lock:
            self._execute_item(sql.UPSERT_ITEM, item)

    def update_item(self, item: Item) -> None:
        with self._lock, immediate_transaction(self._connection):
            self._replace(item)

    def group_item(self, child: Item) -> None:
        parent_id = require_parent(child)
        with self._lock, immediate_transaction(self._connection):
            self._require_stored(child.id)
            self._require_groupable_parent(parent_id)
            self._require_no_children(child.id)
            self._execute_item(sql.UPDATE_ITEM, child)

    def record_completion(self, item: Item, outcome: Outcome) -> None:
        require_outcome_for_item(item, outcome)
        with self._lock, immediate_transaction(self._connection):
            self._replace(item)
            self._insert_outcome(outcome)

    def add_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            self._insert_outcome(outcome)

    def save_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            try:
                self._connection.execute(sql.UPSERT_OUTCOME, outcome_values(outcome))
            except sqlite3.IntegrityError as error:
                self._refuse_outcome(outcome, error)

    def _replace(self, item: Item) -> None:
        self._require_stored(item.id)
        self._execute_item(sql.UPDATE_ITEM, item)

    def _require_stored(self, item_id: str) -> None:
        if self._stored(item_id) is None:
            raise UnknownItemError(item_id)

    def _require_groupable_parent(self, parent_id: str) -> None:
        parent = self._stored(parent_id)
        if parent is None:
            raise UnknownItemError(parent_id)
        if parent.parent_id is not None:
            raise ParentIsGroupedError(parent_id)

    def _require_no_children(self, item_id: str) -> None:
        if self._exists(sql.ITEM_HOLDS_ITEMS, item_id):
            raise ChildHoldsItemsError(item_id)

    def _stored(self, item_id: str) -> Item | None:
        row = self._connection.execute(sql.ITEM_BY_ID, (item_id,)).fetchone()
        return None if row is None else item_from_row(row)

    def _execute_item(self, statement: str, item: Item) -> None:
        try:
            self._connection.execute(statement, item_values(item))
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorname != _FOREIGN_KEY_VIOLATION:
                raise
            self._refuse_item(item, error)

    def _refuse_item(self, item: Item, error: sqlite3.IntegrityError) -> NoReturn:
        if not self._exists(sql.CAPTURE_EXISTS, item.capture_id):
            raise UnknownCaptureError(item.capture_id) from error
        if item.parent_id is not None:
            raise UnknownItemError(item.parent_id) from error
        raise error

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

    def _exists(self, query: str, row_id: str) -> bool:
        return self._connection.execute(query, (row_id,)).fetchone() is not None
