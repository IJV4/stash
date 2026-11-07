import datetime as dt
from dataclasses import replace
from itertools import islice

from stash.domain import Item, NudgeKey, NudgeKind, Stage, Step, require_aware
from stash.nudges.digest import (
    FORGOTTEN_LIMIT,
    NEW_WINDOW,
    PICK_LIMIT,
    UPCOMING_DAYS,
    DigestSections,
    UpcomingEntry,
    UpcomingItem,
    UpcomingPersonDate,
    UpcomingStep,
)
from stash.nudges.due import WeeklyDigest
from stash.nudges.person_key_dates import PersonKeyDates
from stash.nudges.ports import DigestStore, PeopleReads, PickSource
from stash.nudges.schedule import Schedule

DIGEST_CONTEXT = "Pick things worth doing in the coming week."
PREVIOUS_DIGESTS = 4
MAX_PREVIOUSLY_SHOWN = FORGOTTEN_LIMIT * PREVIOUS_DIGESTS
FORGOTTEN_FETCH_LIMIT = MAX_PREVIOUSLY_SHOWN + FORGOTTEN_LIMIT
PREVIOUS_DIGESTS_WINDOW = dt.timedelta(weeks=PREVIOUS_DIGESTS, days=1)


class DigestBuilder:
    def __init__(
        self, store: DigestStore, picks: PickSource, schedule: Schedule, people: PeopleReads
    ) -> None:
        self._store = store
        self._picks = picks
        self._forgotten = _Forgotten(store, schedule)
        self._upcoming = _Upcoming(store, schedule, people)

    def build(self, due: WeeklyDigest, now: dt.datetime) -> WeeklyDigest:
        require_aware("now", now)
        sections = DigestSections(
            new_items=self._new_items(due.due_at),
            forgotten=self._forgotten.items(due.due_at),
            upcoming=self._upcoming.entries(now),
            picks=self._picks.picks(DIGEST_CONTEXT, PICK_LIMIT),
        )
        return replace(due, sections=sections)

    def _new_items(self, digest_at: dt.datetime) -> tuple[Item, ...]:
        created = self._store.created_between(digest_at - NEW_WINDOW, digest_at)
        return tuple(item for item in created if item.stage is not Stage.DROPPED)


class _Forgotten:
    def __init__(self, store: DigestStore, schedule: Schedule) -> None:
        self._store = store
        self._schedule = schedule

    def items(self, digest_at: dt.datetime) -> tuple[Item, ...]:
        cutoff = self._schedule.forgotten_cutoff(digest_at)
        candidates = self._store.want_to_older_than(cutoff, FORGOTTEN_FETCH_LIMIT)
        previous = self._previous_digests(digest_at)
        fresh = (item for item in candidates if not self._shown_in_any(item, previous))
        return tuple(islice(fresh, FORGOTTEN_LIMIT))

    def _previous_digests(self, digest_at: dt.datetime) -> list[dt.datetime]:
        start = digest_at - PREVIOUS_DIGESTS_WINDOW
        instants = self._schedule.digest_instants_between(start, digest_at)
        return [instant for instant in instants if instant < digest_at]

    def _shown_in_any(self, item: Item, digests: list[dt.datetime]) -> bool:
        return any(
            self._store.was_sent(NudgeKey.of(NudgeKind.FORGOTTEN, item.id, instant))
            for instant in digests
        )


class _Upcoming:
    def __init__(self, store: DigestStore, schedule: Schedule, people: PeopleReads) -> None:
        self._store = store
        self._schedule = schedule
        self._key_dates = PersonKeyDates(people)

    def entries(self, now: dt.datetime) -> tuple[UpcomingEntry, ...]:
        first = self._schedule.local_date(now)
        last = first + dt.timedelta(days=UPCOMING_DAYS)
        entries: list[UpcomingEntry] = [
            *self._dated_items(first, last),
            *self._steps(first, last),
            *self._person_dates(first, last),
        ]
        return tuple(sorted(entries, key=lambda entry: (entry.on, entry.RANK)))

    def _dated_items(self, first: dt.date, last: dt.date) -> list[UpcomingItem]:
        return [
            UpcomingItem(item.date, item)
            for item in self._store.items_dated_between(first, last)
            if item.date is not None and not item.is_closed
        ]

    def _steps(self, first: dt.date, last: dt.date) -> list[UpcomingStep]:
        entries = (self._step_entry(step) for step in self._store.open_confirmed_steps())
        return [entry for entry in entries if entry is not None and first <= entry.on <= last]

    def _person_dates(self, first: dt.date, last: dt.date) -> list[UpcomingPersonDate]:
        return [
            UpcomingPersonDate(on, person, key_date)
            for person, key_date, on in self._key_dates.between(first, last)
        ]

    def _step_entry(self, step: Step) -> UpcomingStep | None:
        item = self._store.get_item(step.item_id)
        if item is None or item.is_closed:
            return None
        day = step.due_date(item.date)
        return None if day is None else UpcomingStep(day, item, step)
