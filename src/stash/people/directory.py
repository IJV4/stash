from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime

from stash.domain import KeyDate, KeyDateKind, Person
from stash.people.ports import PeopleBook
from stash.people.results import Resolution
from stash.store.port import UnknownPersonError


class PeopleDirectory:
    def __init__(
        self, store: PeopleBook, new_id: Callable[[], str], clock: Callable[[], datetime]
    ) -> None:
        self._store = store
        self._new_id = new_id
        self._clock = clock

    def add(self, name: str, relation: str = "", aliases: Sequence[str] = ()) -> Person:
        person = Person(
            id=self._new_id(),
            name=name,
            relation=relation,
            aliases=tuple(aliases),
            notes="",
            created_at=self._clock(),
        )
        self._store.save_person(person)
        return person

    def rename(self, person_id: str, name: str) -> Person:
        return self._saved(replace(self._person(person_id), name=name))

    def add_alias(self, person_id: str, alias: str) -> Person:
        person = self._person(person_id)
        return self._saved(replace(person, aliases=(*person.aliases, alias)))

    def remove(self, person_id: str) -> None:
        self._person(person_id)
        self._store.delete_person(person_id)

    def add_key_date(
        self,
        person_id: str,
        kind: KeyDateKind,
        month: int,
        day: int,
        year: int | None = None,
        label: str = "",
    ) -> KeyDate:
        key_date = KeyDate(
            id=self._new_id(),
            person_id=person_id,
            kind=kind,
            label=label,
            month=month,
            day=day,
            year=year,
        )
        self._store.save_key_date(key_date)
        return key_date

    def resolve(self, names: Sequence[str]) -> Resolution:
        linked: dict[str, Person] = {}
        unknown: dict[str, str] = {}
        for name in _non_blank_names(names):
            person = self._store.find_by_name(name)
            if person is None:
                unknown.setdefault(name.casefold(), name)
            else:
                linked.setdefault(person.id, person)
        return Resolution(tuple(linked.values()), tuple(unknown.values()))

    def _person(self, person_id: str) -> Person:
        person = self._store.get_person(person_id)
        if person is None:
            raise UnknownPersonError(person_id)
        return person

    def _saved(self, person: Person) -> Person:
        self._store.save_person(person)
        return person


def _non_blank_names(names: Sequence[str]) -> list[str]:
    stripped = (name.strip() for name in names)
    return [name for name in stripped if name]
