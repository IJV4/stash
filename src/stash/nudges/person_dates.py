import datetime as dt

from stash.domain import ItemType, KeyDate, Person
from stash.nudges.due import PersonDateReminder
from stash.nudges.person_key_dates import PersonKeyDates
from stash.nudges.ports import PeopleReads
from stash.nudges.schedule import Schedule


class PersonDates:
    def __init__(self, people: PeopleReads, schedule: Schedule, lead_days: tuple[int, ...]) -> None:
        self._people = people
        self._key_dates = PersonKeyDates(people)
        self._schedule = schedule
        self._lead_days = lead_days

    def reminders(self, first: dt.date, last: dt.date) -> list[PersonDateReminder]:
        horizon = last + dt.timedelta(days=max(self._lead_days))
        return [
            self._reminder(person, key_date, on, lead)
            for person, key_date, on in self._key_dates.between(first, horizon)
            for lead in self._lead_days
            if first <= on - dt.timedelta(days=lead) <= last
        ]

    def _reminder(
        self, person: Person, key_date: KeyDate, on: dt.date, lead: int
    ) -> PersonDateReminder:
        gifts = self._people.items_for(person.id, ItemType.GIFT)
        ideas = tuple(gift.title for gift in gifts if not gift.is_closed)
        due_at = self._schedule.reminder_at(on - dt.timedelta(days=lead))
        return PersonDateReminder(person, key_date, on, lead, ideas, due_at)
