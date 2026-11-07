import datetime as dt

from stash.domain import KeyDate, Person
from stash.nudges.ports import PeopleReads


def require_key_date_of(person: Person, key_date: KeyDate) -> None:
    if key_date.person_id != person.id:
        raise ValueError(f"key date {key_date.id!r} belongs to {key_date.person_id!r}")


class PersonKeyDates:
    def __init__(self, people: PeopleReads) -> None:
        self._people = people

    def between(self, first: dt.date, last: dt.date) -> list[tuple[Person, KeyDate, dt.date]]:
        found = (
            (self._people.get_person(key_date.person_id), key_date, on)
            for key_date, on in self._people.key_dates_between(first, last)
        )
        return [(person, key_date, on) for person, key_date, on in found if person]
