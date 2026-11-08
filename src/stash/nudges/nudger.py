import datetime as dt
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Protocol, TypeVar

from stash.domain import Item, NudgeKind, Stage, Step, require_aware
from stash.nudges.due import (
    DateReminder,
    DueNudge,
    FollowUp,
    PersonDateReminder,
    StepReminder,
    StuckItem,
    WeeklyDigest,
)
from stash.nudges.messages import NudgeMessage
from stash.nudges.person_dates import PersonDates
from stash.nudges.schedule import Schedule
from stash.store.port import Store

LOOKBACK = dt.timedelta(days=14)
STUCK_LIMIT = 10
STEP_REMINDER_STAGES = frozenset({Stage.PLANNED, Stage.DOING})


class _Timed(Protocol):
    @property
    def due_at(self) -> dt.datetime: ...


Due = TypeVar("Due", bound=_Timed)


@dataclass(frozen=True, slots=True)
class DueWindow:
    start: dt.datetime
    now: dt.datetime

    def keep(self, dues: Iterable[Due]) -> list[Due]:
        return [due for due in dues if self.start <= due.due_at <= self.now]


def _dated(items: Iterable[Item]) -> Iterator[tuple[Item, dt.date]]:
    return ((item, item.date) for item in items if item.date is not None)


class Nudger:
    def __init__(self, store: Store, schedule: Schedule, person_dates: PersonDates) -> None:
        self._store = store
        self._schedule = schedule
        self._person_dates = person_dates

    def due(self, now: dt.datetime) -> list[DueNudge]:
        require_aware("now", now)
        window = DueWindow(now - LOOKBACK, now)
        found: list[DueNudge] = [
            *self._step_reminders(window),
            *self._date_reminders(window),
            *self._person_date_reminders(window),
            *self._follow_ups(window),
            *self._digest(window),
        ]
        unsent = [due for due in found if not self._store.was_sent(due.nudge.key)]
        return sorted(unsent, key=lambda due: due.due_at)

    def is_first_run(self) -> bool:
        return self._store.last_sent(NudgeKind.DIGEST) is None

    def mark_sent(self, message: NudgeMessage, sent_at: dt.datetime) -> bool:
        return self._store.record_all_sent(message.nudges, sent_at)

    def _step_reminders(self, window: DueWindow) -> list[StepReminder]:
        reminders = (self._step_reminder(step) for step in self._store.open_confirmed_steps())
        return window.keep(reminder for reminder in reminders if reminder is not None)

    def _step_reminder(self, step: Step) -> StepReminder | None:
        item = self._store.get_item(step.item_id)
        if item is None or item.stage not in STEP_REMINDER_STAGES:
            return None
        day = step.due_date(item.date)
        if day is None:
            return None
        return StepReminder(step, item, self._schedule.reminder_at(day))

    def _date_reminders(self, window: DueWindow) -> list[DateReminder]:
        first, last = self._local_dates(window)
        planned = (
            (item, day)
            for item, day in _dated(self._store.items_dated_between(first, last))
            if item.is_planned
        )
        return window.keep(
            DateReminder(item, day, self._schedule.reminder_at(day)) for item, day in planned
        )

    def _person_date_reminders(self, window: DueWindow) -> list[PersonDateReminder]:
        return window.keep(self._person_dates.reminders(window.now))

    def _follow_ups(self, window: DueWindow) -> list[FollowUp]:
        if self._followup_slot_taken(window.now):
            return []
        first, last = self._schedule.item_dates_followed_up_between(*self._local_dates(window))
        items = self._store.planned_awaiting_outcome_dated_between(first, last)
        return window.keep(
            FollowUp(item, self._schedule.followup_at(day)) for item, day in _dated(items)
        )

    def _followup_slot_taken(self, now: dt.datetime) -> bool:
        last = self._store.last_sent(NudgeKind.FOLLOWUP)
        return last is not None and last >= self._schedule.latest_followup_slot(now)

    def _digest(self, window: DueWindow) -> list[WeeklyDigest]:
        instant = self._schedule.latest_digest_between(window.start, window.now)
        if instant is None:
            return []
        return [WeeklyDigest(instant, self._stuck_items(instant))]

    def _stuck_items(self, instant: dt.datetime) -> tuple[StuckItem, ...]:
        cutoff = self._schedule.stuck_cutoff(instant)
        stuck = (
            StuckItem(item, instant) for item in self._store.doing_older_than(cutoff, STUCK_LIMIT)
        )
        return tuple(item for item in stuck if not self._store.was_sent(item.nudge.key))

    def _local_dates(self, window: DueWindow) -> tuple[dt.date, dt.date]:
        return self._schedule.local_date(window.start), self._schedule.local_date(window.now)
