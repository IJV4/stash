import calendar
import datetime as dt
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from stash.domain._validation import (
    frozen_strings,
    require_aware,
    require_max_length,
    require_text,
)
from stash.domain.wire import require_wire_safe_id

PERSON_NAME_LIMIT = 80
PERSON_RELATION_LIMIT = 40
MAX_ROSTER_WINDOW_DAYS = 366
MAX_ALIASES = 5
PERSON_NOTES_LIMIT = 1000
KEY_DATE_LABEL_LIMIT = 60
LEAP_YEAR = 2000
FEBRUARY = 2
LEAP_DAY = 29
COMMON_YEAR_LAST_FEBRUARY_DAY = 28


class KeyDateKind(StrEnum):
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    OTHER = "other"


def matching_key(name: str) -> str:
    return unicodedata.normalize("NFC", name.strip()).casefold()


def _require_name(name: str, value: str) -> None:
    require_text(name, value)
    require_max_length(name, value, PERSON_NAME_LIMIT)


@dataclass(frozen=True, slots=True)
class Person:
    id: str
    name: str
    relation: str
    aliases: tuple[str, ...]
    notes: str
    created_at: dt.datetime

    def __post_init__(self) -> None:
        require_wire_safe_id("person id", self.id)
        _require_name("name", self.name)
        require_max_length("relation", self.relation, PERSON_RELATION_LIMIT)
        object.__setattr__(self, "aliases", frozen_strings("aliases", self.aliases))
        if len(self.aliases) > MAX_ALIASES:
            raise ValueError(f"a person has at most {MAX_ALIASES} aliases")
        for alias in self.aliases:
            _require_name("alias", alias)
        require_max_length("notes", self.notes, PERSON_NOTES_LIMIT)
        require_aware("created_at", self.created_at)

    @property
    def names(self) -> frozenset[str]:
        return frozenset(matching_key(name) for name in (self.name, *self.aliases))

    def answers_to(self, name: str) -> bool:
        return matching_key(name) in self.names

    def shares_a_name_with(self, other: "Person") -> bool:
        return not self.names.isdisjoint(other.names)


@dataclass(frozen=True, slots=True)
class KeyDate:
    id: str
    person_id: str
    kind: KeyDateKind
    label: str
    month: int
    day: int
    year: int | None

    def __post_init__(self) -> None:
        require_wire_safe_id("key date id", self.id)
        require_wire_safe_id("key date person id", self.person_id)
        require_max_length("label", self.label, KEY_DATE_LABEL_LIMIT)
        self._require_calendar_date()

    def next_occurrence(self, today: dt.date) -> dt.date:
        this_year = self._in_year(today.year)
        return this_year if this_year >= today else self._in_year(today.year + 1)

    def years_on(self, occurrence: dt.date) -> int | None:
        return None if self.year is None else occurrence.year - self.year

    def _require_calendar_date(self) -> None:
        try:
            dt.date(LEAP_YEAR if self.year is None else self.year, self.month, self.day)
        except ValueError as error:
            raise ValueError(f"{self.month}/{self.day}/{self.year} is not a real date") from error

    def _in_year(self, year: int) -> dt.date:
        if (self.month, self.day) == (FEBRUARY, LEAP_DAY) and not calendar.isleap(year):
            return dt.date(year, FEBRUARY, COMMON_YEAR_LAST_FEBRUARY_DAY)
        return dt.date(year, self.month, self.day)


@dataclass(frozen=True, slots=True)
class NextKeyDate:
    key_date: KeyDate
    on: dt.date


@dataclass(frozen=True, slots=True)
class PersonSummary:
    person: Person
    next_date: NextKeyDate | None


def occurrences_between(
    key_dates: Iterable[KeyDate], start: dt.date, end: dt.date
) -> list[tuple[KeyDate, dt.date]]:
    occurrences = ((key_date, key_date.next_occurrence(start)) for key_date in key_dates)
    within = [(key_date, day) for key_date, day in occurrences if day <= end]
    return sorted(within, key=lambda pair: (pair[1], pair[0].id))
