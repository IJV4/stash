import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta

from stash.domain import (
    MAX_ROSTER_WINDOW_DAYS,
    KeyDate,
    KeyDateKind,
    NextKeyDate,
    Person,
    PersonSummary,
    matching_key,
)
from stash.people.results import Resolution
from stash.store.port import Store, UnknownPersonError

logger = logging.getLogger(__name__)


class PeopleDirectory:
    def __init__(
        self, store: Store, new_id: Callable[[], str], clock: Callable[[], datetime]
    ) -> None:
        self._store = store
        self._new_id = new_id
        self._clock = clock

    def add(self, name: str, relation: str = "", aliases: Sequence[str] = ()) -> Person:
        return self._saved(
            Person(
                id=self._new_id(),
                name=name,
                relation=relation,
                aliases=tuple(aliases),
                notes="",
                created_at=self._clock(),
            )
        )

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
            id=self._existing_key_date_id(person_id, kind, label) or self._new_id(),
            person_id=person_id,
            kind=kind,
            label=label,
            month=month,
            day=day,
            year=year,
        )
        self._store.save_key_date(key_date)
        return key_date

    def link(self, item_id: str, person_id: str) -> None:
        self._store.link(item_id, person_id)

    def roster(self, today: date, within_days: int | None = None) -> tuple[PersonSummary, ...]:
        horizon = MAX_ROSTER_WINDOW_DAYS if within_days is None else within_days
        next_dates = self._next_dates(today, today + timedelta(days=horizon))
        summaries = [
            PersonSummary(person, next_dates.get(person.id)) for person in self._store.list_people()
        ]
        wanted = [item for item in summaries if within_days is None or item.next_date is not None]
        return tuple(sorted(wanted, key=_by_next_date))

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

    def _next_dates(self, first: date, last: date) -> dict[str, NextKeyDate]:
        next_dates: dict[str, NextKeyDate] = {}
        for key_date, on in self._store.key_dates_between(first, last):
            next_dates.setdefault(key_date.person_id, NextKeyDate(key_date, on))
        return next_dates

    def _person(self, person_id: str) -> Person:
        person = self._store.get_person(person_id)
        if person is None:
            raise UnknownPersonError(person_id)
        return person

    def _saved(self, person: Person) -> Person:
        self._store.save_person(person)
        self._link_items_naming(person)
        return person

    def _link_items_naming(self, person: Person) -> None:
        try:
            for item in self._store.items_naming_people():
                if any(person.answers_to(name) for name in item.people):
                    self._store.link(item.id, person.id)
        except Exception:
            logger.exception(
                "linking existing items to person %s failed; the person stays", person.id
            )

    def _existing_key_date_id(self, person_id: str, kind: KeyDateKind, label: str) -> str | None:
        same = (
            key_date.id
            for key_date in self._store.key_dates_for(person_id)
            if key_date.kind is kind and matching_key(key_date.label) == matching_key(label)
        )
        return next(same, None)


def _non_blank_names(names: Sequence[str]) -> list[str]:
    stripped = (name.strip() for name in names)
    return [name for name in stripped if name]


def _by_next_date(summary: PersonSummary) -> tuple[int, date, str]:
    name = summary.person.name.casefold()
    if summary.next_date is None:
        return (1, date.max, name)
    return (0, summary.next_date.on, name)
