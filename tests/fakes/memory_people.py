import threading
from datetime import date

from stash.domain import Item, ItemType, KeyDate, Person, occurrences_between
from stash.store.port import (
    UnknownItemError,
    UnknownPersonError,
    find_named,
    require_date_range,
    require_distinct_names,
)


class MemoryPeople:
    def __init__(self, lock: threading.RLock, items: dict[str, Item]) -> None:
        self._lock = lock
        self._items = items
        self._people: dict[str, Person] = {}
        self._key_dates: dict[str, KeyDate] = {}
        self._links: set[tuple[str, str]] = set()

    def save_person(self, person: Person) -> None:
        with self._lock:
            require_distinct_names(person, self.list_people())
            self._people[person.id] = person

    def get_person(self, person_id: str) -> Person | None:
        with self._lock:
            return self._people.get(person_id)

    def delete_person(self, person_id: str) -> None:
        with self._lock:
            self._people.pop(person_id, None)
            self._key_dates = {
                key_date_id: key_date
                for key_date_id, key_date in self._key_dates.items()
                if key_date.person_id != person_id
            }
            self._links = {link for link in self._links if link[1] != person_id}

    def list_people(self) -> list[Person]:
        with self._lock:
            people = list(self._people.values())
        return sorted(people, key=lambda person: (person.name.casefold(), person.id))

    def find_by_name(self, name: str) -> Person | None:
        return find_named(self.list_people(), name)

    def save_key_date(self, key_date: KeyDate) -> None:
        with self._lock:
            self._require_person(key_date.person_id)
            self._key_dates[key_date.id] = key_date

    def delete_key_date(self, key_date_id: str) -> None:
        with self._lock:
            self._key_dates.pop(key_date_id, None)

    def key_dates_for(self, person_id: str) -> list[KeyDate]:
        with self._lock:
            own = [
                key_date for key_date in self._key_dates.values() if key_date.person_id == person_id
            ]
        return sorted(own, key=lambda key_date: (key_date.month, key_date.day, key_date.id))

    def key_dates_between(self, start: date, end: date) -> list[tuple[KeyDate, date]]:
        require_date_range(start, end)
        with self._lock:
            key_dates = list(self._key_dates.values())
        return occurrences_between(key_dates, start, end)

    def link(self, item_id: str, person_id: str) -> None:
        with self._lock:
            if item_id not in self._items:
                raise UnknownItemError(item_id)
            self._require_person(person_id)
            self._links.add((item_id, person_id))

    def unlink(self, item_id: str, person_id: str) -> None:
        with self._lock:
            self._links.discard((item_id, person_id))

    def people_for(self, item_id: str) -> list[Person]:
        with self._lock:
            linked = [
                self._people[person_id]
                for linked_item, person_id in self._links
                if linked_item == item_id
            ]
        return sorted(linked, key=lambda person: (person.name.casefold(), person.id))

    def items_for(self, person_id: str, item_type: ItemType | None = None) -> list[Item]:
        with self._lock:
            linked = [
                self._items[item_id]
                for item_id, linked_person in self._links
                if linked_person == person_id
            ]
        matching = [item for item in linked if item_type is None or item.item_type is item_type]
        return sorted(matching, key=lambda item: (item.created_at, item.id), reverse=True)

    def drop_links_of_item(self, item_id: str) -> None:
        with self._lock:
            self._links = {link for link in self._links if link[0] != item_id}

    def _require_person(self, person_id: str) -> None:
        if person_id not in self._people:
            raise UnknownPersonError(person_id)
