from nudge_builders import (
    BOOK_THE_TABLE_ID,
    SATURDAY,
    SATURDAY_MORNING,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    a_planned_date_night,
    a_same_day_step,
    a_stuck_book,
)
from planning_builders import DATE_NIGHT_ID

from stash.domain import Nudge, NudgeKind
from stash.nudges import DateReminder, FollowUp, StepReminder, StuckItem, WeeklyDigest


def test_a_step_reminder_is_the_step_nudge_titled_with_the_step_text() -> None:
    # Setup
    reminder = StepReminder(a_same_day_step(), a_planned_date_night(), SATURDAY_MORNING)

    # Execute
    nudge = reminder.nudge

    # Assert
    assert nudge == Nudge(NudgeKind.STEP, BOOK_THE_TABLE_ID, SATURDAY_MORNING, "Book the table")


def test_a_date_reminder_is_the_item_date_nudge_titled_with_the_item_title() -> None:
    # Setup
    reminder = DateReminder(a_planned_date_night(), SATURDAY, SATURDAY_MORNING)

    # Execute
    nudge = reminder.nudge

    # Assert
    assert nudge == Nudge(NudgeKind.ITEM_DATE, DATE_NIGHT_ID, SATURDAY_MORNING, "Date night")


def test_a_follow_up_is_the_follow_up_nudge_titled_with_the_item_title() -> None:
    # Setup
    follow_up = FollowUp(a_planned_date_night(), SUNDAY_MORNING)

    # Execute
    nudge = follow_up.nudge

    # Assert
    assert nudge == Nudge(NudgeKind.FOLLOWUP, DATE_NIGHT_ID, SUNDAY_MORNING, "Date night")


def test_a_stuck_item_is_the_stuck_nudge_titled_with_the_item_title() -> None:
    # Setup
    stuck = StuckItem(a_stuck_book(), SUNDAY_DIGEST_TIME)

    # Execute
    nudge = stuck.nudge

    # Assert
    assert nudge == Nudge(
        NudgeKind.STUCK, "systems-book", SUNDAY_DIGEST_TIME, "Thinking in Systems"
    )


def test_the_weekly_digest_is_the_digest_nudge_for_the_weekly_subject() -> None:
    # Setup
    digest = WeeklyDigest(SUNDAY_DIGEST_TIME, ())

    # Execute
    nudge = digest.nudge

    # Assert
    assert nudge == Nudge(NudgeKind.DIGEST, "weekly", SUNDAY_DIGEST_TIME, "Weekly digest")


def test_a_digest_stands_for_its_stuck_items_and_then_itself() -> None:
    # Setup
    stuck = StuckItem(a_stuck_book(), SUNDAY_DIGEST_TIME)
    digest = WeeklyDigest(SUNDAY_DIGEST_TIME, (stuck,))

    # Execute
    nudges = digest.nudges

    # Assert
    assert nudges == (stuck.nudge, digest.nudge)


def test_a_digest_with_no_stuck_items_stands_for_itself_alone() -> None:
    # Setup
    digest = WeeklyDigest(SUNDAY_DIGEST_TIME, ())

    # Execute
    nudges = digest.nudges

    # Assert
    assert nudges == (digest.nudge,)


def test_a_due_nudge_reports_the_instant_it_was_due() -> None:
    # Setup
    follow_up = FollowUp(a_planned_date_night(), SUNDAY_MORNING)

    # Execute
    due_at = follow_up.due_at

    # Assert
    assert due_at == SUNDAY_MORNING
