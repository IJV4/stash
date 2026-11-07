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

    def reminders(self, now: dt.datetime) -> list[PersonDateReminder]:
        today = self._schedule.local_date(now)
        horizon = today + dt.timedelta(days=max(self._lead_days))
        reminders: list[PersonDateReminder] = []
        for person, key_date, on in self._key_dates.between(today, horizon):
            lead = self._closest_started_lead(on, now, today)
            if lead is not None:
                reminders.append(self._reminder(person, key_date, on, lead, (on - today).days))
        return reminders

    def _closest_started_lead(self, on: dt.date, now: dt.datetime, today: dt.date) -> int | None:
        started = (
            lead
            for lead in self._lead_days
            if self._lead_instant(on, lead) <= now and (lead == 0 or today < on)
        )
        return min(started, default=None)

    def _lead_instant(self, on: dt.date, lead: int) -> dt.datetime:
        return self._schedule.reminder_at(on - dt.timedelta(days=lead))

    def _reminder(
        self, person: Person, key_date: KeyDate, on: dt.date, lead: int, days_left: int
    ) -> PersonDateReminder:
        gifts = self._people.items_for(person.id, ItemType.GIFT)
        ideas = tuple(gift.title for gift in gifts if not gift.is_closed)
        return PersonDateReminder(
            person, key_date, on, lead, days_left, ideas, self._lead_instant(on, lead)
        )
