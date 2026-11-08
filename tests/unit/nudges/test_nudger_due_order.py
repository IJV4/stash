from builders import stored
from fakes.store_factories import FreshStore
from nudge_builders import (
    SUNDAY,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    SUNDAY_NOON,
    a_date_reminder,
    a_follow_up,
    a_nudger,
    a_planned_date_night,
    a_step_due_on,
    a_step_reminder,
    a_weekly_digest,
    stored_date_night_week,
    stored_step,
)

from stash.nudges import StepReminder, WeeklyDigest


def test_everything_due_at_once_comes_back_oldest_first() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_week(store)

    # Execute
    due = a_nudger(store).due(SUNDAY_NOON)

    # Assert
    assert due == [a_step_reminder(), a_date_reminder(), a_follow_up(), a_weekly_digest()]


def test_a_step_due_after_a_date_reminder_is_listed_after_it() -> None:
    # Setup
    store = FreshStore()
    date_night = stored(store, a_planned_date_night())
    stored_step(store, a_step_due_on(SUNDAY))

    # Execute
    due = a_nudger(store).due(SUNDAY_NOON)

    # Assert
    assert due == [
        a_date_reminder(),
        StepReminder(a_step_due_on(SUNDAY), date_night, SUNDAY_MORNING),
        a_follow_up(),
        WeeklyDigest(SUNDAY_DIGEST_TIME, ()),
    ]
