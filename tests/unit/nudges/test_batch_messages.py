from datetime import timedelta

from builders import MICROSECOND, in_los_angeles
from nudge_builders import (
    SUNDAY,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    a_date_reminder,
    a_follow_up,
    a_step_reminder,
    a_weekly_digest,
)

from stash.nudges import NudgeMessage, batch_messages

NOW = SUNDAY_DIGEST_TIME
THIRTY_MINUTES = timedelta(minutes=30)


def test_nothing_due_makes_no_messages() -> None:
    # Execute
    messages = batch_messages([], NOW)

    # Assert
    assert messages == ()


def test_step_and_date_reminders_share_one_message() -> None:
    # Setup
    step, date = a_step_reminder(NOW), a_date_reminder(NOW)

    # Execute
    messages = batch_messages([step, date], NOW)

    # Assert
    assert messages == (NudgeMessage((step, date), catch_up=False),)


def test_reminders_follow_ups_and_the_digest_make_one_message_each_in_that_order() -> None:
    # Setup
    reminder, follow_up, digest = a_step_reminder(NOW), a_follow_up(NOW), a_weekly_digest(NOW)

    # Execute
    messages = batch_messages([digest, follow_up, reminder], NOW)

    # Assert
    assert messages == (
        NudgeMessage((reminder,), catch_up=False),
        NudgeMessage((follow_up,), catch_up=False),
        NudgeMessage((digest,), catch_up=False),
    )


def test_a_single_message_that_is_a_day_overdue_is_not_a_catch_up() -> None:
    # Setup
    reminder = a_step_reminder(NOW - timedelta(days=1))

    # Execute
    messages = batch_messages([reminder], NOW)

    # Assert
    assert messages == (NudgeMessage((reminder,), catch_up=False),)


def test_a_single_message_just_under_thirty_minutes_overdue_is_not_a_catch_up() -> None:
    # Setup
    reminder = a_step_reminder(NOW - THIRTY_MINUTES + MICROSECOND)

    # Execute
    messages = batch_messages([reminder], NOW)

    # Assert
    assert messages == (NudgeMessage((reminder,), catch_up=False),)


def test_several_messages_exactly_thirty_minutes_overdue_stay_separate() -> None:
    # Setup
    reminder, follow_up = a_step_reminder(NOW - THIRTY_MINUTES), a_follow_up(NOW)

    # Execute
    messages = batch_messages([reminder, follow_up], NOW)

    # Assert
    assert messages == (
        NudgeMessage((reminder,), catch_up=False),
        NudgeMessage((follow_up,), catch_up=False),
    )


def test_several_messages_thirty_minutes_and_a_microsecond_overdue_become_one_catch_up() -> None:
    # Setup
    reminder = a_step_reminder(NOW - THIRTY_MINUTES - MICROSECOND)
    follow_up = a_follow_up(NOW)

    # Execute
    messages = batch_messages([reminder, follow_up], NOW)

    # Assert
    assert messages == (NudgeMessage((reminder, follow_up), catch_up=True),)


def test_a_catch_up_carries_reminders_then_follow_ups_then_the_digest() -> None:
    # Setup
    reminder = a_step_reminder(in_los_angeles(SUNDAY, 6))
    follow_up, digest = a_follow_up(SUNDAY_MORNING), a_weekly_digest(NOW)

    # Execute
    messages = batch_messages([reminder, follow_up, digest], NOW)

    # Assert
    assert messages == (NudgeMessage((reminder, follow_up, digest), catch_up=True),)


def test_a_catch_up_is_judged_by_the_oldest_nudge_not_the_newest() -> None:
    # Setup
    old, fresh = a_follow_up(NOW - timedelta(hours=3)), a_weekly_digest(NOW)

    # Execute
    messages = batch_messages([fresh, old], NOW)

    # Assert
    assert [message.catch_up for message in messages] == [True]


def test_several_days_of_follow_ups_alone_are_one_message_and_not_a_catch_up() -> None:
    # Setup
    yesterday, today = a_follow_up(NOW - timedelta(days=1)), a_follow_up(NOW)

    # Execute
    messages = batch_messages([yesterday, today], NOW)

    # Assert
    assert messages == (NudgeMessage((yesterday, today), catch_up=False),)
