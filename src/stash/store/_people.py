import sqlite3
import threading
from datetime import date

from stash.domain import Item, ItemType, KeyDate, Person, occurrences_between
from stash.store import _sql as sql
from stash.store._rows import (
    item_from_row,
    key_date_from_row,
    key_date_values,
    person_from_row,
    person_values,
)
from stash.store._transaction import immediate_transaction
from stash.store.port import (
    UnknownItemError,
    UnknownPersonError,
    find_named,
    require_date_range,
    require_distinct_names,
)


class SqlitePeople:
    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    def save_person(self, person: Person) -> None:
        with self._lock, immediate_transaction(self._connection):
            require_distinct_names(person, self._all_people())
            self._connection.execute(sql.UPSERT_PERSON, person_values(person))

    def get_person(self, person_id: str) -> Person | None:
        with self._lock:
            row = self._connection.execute(sql.PERSON_BY_ID, (person_id,)).fetchone()
        return None if row is None else person_from_row(row)

    def delete_person(self, person_id: str) -> None:
        with self._lock:
            self._connection.execute(sql.DELETE_PERSON, (person_id,))

    def list_people(self) -> list[Person]:
        with self._lock:
            return self._all_people()

    def find_by_name(self, name: str) -> Person | None:
        return find_named(self.list_people(), name)

    def save_key_date(self, key_date: KeyDate) -> None:
        with self._lock, immediate_transaction(self._connection):
            self._require_person(key_date.person_id)
            self._connection.execute(sql.UPSERT_KEY_DATE, key_date_values(key_date))

    def delete_key_date(self, key_date_id: str) -> None:
        with self._lock:
            self._connection.execute(sql.DELETE_KEY_DATE, (key_date_id,))

    def key_dates_for(self, person_id: str) -> list[KeyDate]:
        with self._lock:
            rows = self._connection.execute(sql.KEY_DATES_FOR_PERSON, (person_id,)).fetchall()
        return [key_date_from_row(row) for row in rows]

    def key_dates_between(self, start: date, end: date) -> list[tuple[KeyDate, date]]:
        require_date_range(start, end)
        with self._lock:
            rows = self._connection.execute(sql.ALL_KEY_DATES).fetchall()
        return occurrences_between([key_date_from_row(row) for row in rows], start, end)

    def link(self, item_id: str, person_id: str) -> None:
        with self._lock, immediate_transaction(self._connection):
            if self._connection.execute(sql.ITEM_EXISTS, (item_id,)).fetchone() is None:
                raise UnknownItemError(item_id)
            self._require_person(person_id)
            self._connection.execute(sql.LINK_ITEM_TO_PERSON, (item_id, person_id))

    def unlink(self, item_id: str, person_id: str) -> None:
        with self._lock:
            self._connection.execute(sql.UNLINK_ITEM_FROM_PERSON, (item_id, person_id))

    def people_for(self, item_id: str) -> list[Person]:
        with self._lock:
            rows = self._connection.execute(sql.PEOPLE_FOR_ITEM, (item_id,)).fetchall()
        return [person_from_row(row) for row in rows]

    def items_for(self, person_id: str, item_type: ItemType | None = None) -> list[Item]:
        parameters = {
            "person_id": person_id,
            "item_type": None if item_type is None else item_type.value,
        }
        with self._lock:
            rows = self._connection.execute(sql.ITEMS_FOR_PERSON, parameters).fetchall()
        return [item_from_row(row) for row in rows]

    def _all_people(self) -> list[Person]:
        rows = self._connection.execute(sql.ALL_PEOPLE).fetchall()
        return [person_from_row(row) for row in rows]

    def _require_person(self, person_id: str) -> None:
        if self._connection.execute(sql.PERSON_EXISTS, (person_id,)).fetchone() is None:
            raise UnknownPersonError(person_id)
