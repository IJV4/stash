from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any, TypeVar

from builders import LOS_ANGELES, an_item, in_los_angeles, stored
from config_builders import a_nudge_config
from fakes.store_factories import FreshStore
from planning_builders import DATE_NIGHT_ID, a_date_night
from step_builders import a_nudge, a_step

from stash.config.people import DEFAULT_LEAD_DAYS
from stash.domain import Item, ItemType, Nudge, NudgeKind, Stage, Step
from stash.nudges import (
    DateReminder,
    DueNudge,
    FollowUp,
    NudgeMessage,
    Nudger,
    PersonDates,
    Schedule,
    StepReminder,
    StuckItem,
    WeeklyDigest,
)
from stash.store import Store

SATURDAY = date(2027, 2, 13)
FRIDAY = SATURDAY - timedelta(days=1)
SUNDAY = SATURDAY + timedelta(days=1)
MONDAY = SATURDAY + timedelta(days=2)
BOOK_THE_TABLE_ID = "book-table"
STUCK_BOOK_ID = "systems-book"
STUCK_BOOK_TITLE = "Thinking in Systems"
FOURTEEN_DAYS = timedelta(days=14)
LONG_AGO = in_los_angeles(date(2027, 1, 1))
SATURDAY_MORNING = in_los_angeles(SATURDAY, 9)
SUNDAY_MORNING = in_los_angeles(SUNDAY, 9)
SUNDAY_NOON = in_los_angeles(SUNDAY, 12)
SUNDAY_DIGEST_TIME = in_los_angeles(SUNDAY, 10)
BOOK_THE_TABLE_LINE = "⏰ Book the table — for Date night (Sat Feb 13)"
DATE_NIGHT_LINE = "📅 Date night (Sat Feb 13)"
FOLLOW_UP_LINE = "How was Date night?"
FOLLOW_UP_LINE_FRAME = "How was ?"
STEP_TEXT_MAX_LENGTH = 200
LONG_TITLE = "T" * 400
DIGEST_LINE = "🗞 Your weekly digest"
STUCK_BOOK_LINE = "📖 How is Thinking in Systems going?"


def a_planned_date_night(**overrides: Any) -> Item:
    return a_date_night(**{"date": SATURDAY, **overrides})


def a_same_day_step(**overrides: Any) -> Step:
    fields: dict[str, Any] = {
        "id": BOOK_THE_TABLE_ID,
        "item_id": DATE_NIGHT_ID,
        "text": "Book the table",
        "lead_days": 0,
        "due_on": None,
        "confirmed": True,
    }
    return a_step(**{**fields, **overrides})


def a_stuck_book(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "id": STUCK_BOOK_ID,
        "title": STUCK_BOOK_TITLE,
        "item_type": ItemType.BOOK,
        "stage": Stage.DOING,
        "created_at": LONG_AGO,
        "updated_at": LONG_AGO,
    }
    return an_item(**{**fields, **overrides})


def stored_step(store: Store, step: Step) -> Step:
    store.save_step(step)
    return step


def stored_date_night_with_its_step(store: Store, **overrides: Any) -> Item:
    date_night = stored(store, a_planned_date_night(**overrides))
    stored_step(store, a_same_day_step())
    return date_night


def stored_date_night_week(store: Store) -> Item:
    date_night = stored_date_night_with_its_step(store)
    stored(store, a_stuck_book())
    return date_night


def an_undated_date_night(**overrides: Any) -> Item:
    return a_date_night(**{"stage": Stage.WANT_TO, "date": None, **overrides})


def a_step_due_on(day: date, **overrides: Any) -> Step:
    return a_same_day_step(**{"lead_days": None, "due_on": day, **overrides})


def stored_step_due_on(store: Store, day: date, **item_overrides: Any) -> Item:
    item = stored(store, an_undated_date_night(**{"stage": Stage.DOING, **item_overrides}))
    stored_step(store, a_step_due_on(day))
    return item


def a_nudge_schedule(**config_overrides: object) -> Schedule:
    return Schedule(a_nudge_config(**config_overrides), LOS_ANGELES)


def a_person_dates(
    store: Store, schedule: Schedule, lead_days: tuple[int, ...] = DEFAULT_LEAD_DAYS
) -> PersonDates:
    return PersonDates(store, schedule, lead_days)


def a_nudger(
    store: Store, lead_days: tuple[int, ...] = DEFAULT_LEAD_DAYS, **config_overrides: object
) -> Nudger:
    schedule = a_nudge_schedule(**config_overrides)
    return Nudger(store, schedule, a_person_dates(store, schedule, lead_days))


def a_nudge_message(*due: DueNudge, catch_up: bool = False) -> NudgeMessage:
    return NudgeMessage(due, catch_up=catch_up)


def a_store_with_a_pending_follow_up() -> FreshStore:
    store = FreshStore()
    stored(store, a_planned_date_night())
    return store


def a_follow_up_sent_for_another_item() -> Nudge:
    return a_nudge(kind=NudgeKind.FOLLOWUP, subject_id="other", title="Other", due_at=LONG_AGO)


Due = TypeVar("Due")


def only(kind: type[Due], due: Iterable[DueNudge]) -> list[Due]:
    return [nudge for nudge in due if isinstance(nudge, kind)]


def a_step_reminder(due_at: datetime = SATURDAY_MORNING) -> StepReminder:
    return StepReminder(a_same_day_step(), a_planned_date_night(), due_at)


def a_date_reminder(due_at: datetime = SATURDAY_MORNING) -> DateReminder:
    return DateReminder(a_planned_date_night(), SATURDAY, due_at)


def a_follow_up(due_at: datetime = SUNDAY_MORNING) -> FollowUp:
    return FollowUp(a_planned_date_night(), due_at)


def a_weekly_digest(due_at: datetime = SUNDAY_DIGEST_TIME) -> WeeklyDigest:
    return WeeklyDigest(due_at, (StuckItem(a_stuck_book(), due_at),))


def a_numbered_step_reminder(number: int, due_at: datetime = SATURDAY_MORNING) -> StepReminder:
    item = a_planned_date_night(id=f"item-{number}", title=f"Event {number}")
    step = a_same_day_step(id=f"step-{number}", item_id=item.id, text=f"Prepare {number}")
    return StepReminder(step, item, due_at)


def a_numbered_follow_up(number: int, due_at: datetime = SUNDAY_MORNING) -> FollowUp:
    return FollowUp(a_planned_date_night(id=f"item-{number}", title=f"Event {number}"), due_at)


def a_follow_up_whose_line_has(characters: int, number: int = 0) -> FollowUp:
    title = "x" * (characters - len(FOLLOW_UP_LINE_FRAME))
    return FollowUp(a_planned_date_night(id=f"item-{number}", title=title), SUNDAY_MORNING)


def stored_long_step_reminders(store: Store, count: int) -> Item:
    date_night = stored(store, an_undated_date_night(title=LONG_TITLE, stage=Stage.DOING))
    for number in range(count):
        text = f"{number:02d}".ljust(STEP_TEXT_MAX_LENGTH, "x")
        stored_step(store, a_step_due_on(SATURDAY, id=f"step-{number}", text=text, position=number))
    return date_night
