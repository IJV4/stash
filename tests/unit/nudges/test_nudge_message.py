from collections.abc import Callable

import pytest
from nudge_builders import a_date_reminder, a_follow_up, a_step_reminder, a_weekly_digest

from stash.nudges import DateReminder, FollowUp, NudgeMessage, StepReminder


def test_a_message_stands_for_the_nudges_of_everything_it_carries_in_order() -> None:
    # Setup
    reminder, digest = a_step_reminder(), a_weekly_digest()
    message = NudgeMessage((reminder, digest), catch_up=False)

    # Execute
    nudges = message.nudges

    # Assert
    assert nudges == (reminder.nudge, *digest.nudges)


@pytest.mark.parametrize("build", [a_step_reminder, a_date_reminder, a_follow_up])
def test_a_message_carrying_a_reminder_stands_for_exactly_its_own_nudge(
    build: Callable[[], StepReminder | DateReminder | FollowUp],
) -> None:
    # Setup
    reminder = build()

    # Execute
    nudges = NudgeMessage((reminder,), catch_up=False).nudges

    # Assert
    assert nudges == (reminder.nudge,)


def test_a_message_carrying_a_digest_stands_for_its_stuck_items_and_then_the_digest() -> None:
    # Setup
    digest = a_weekly_digest()

    # Execute
    nudges = NudgeMessage((digest,), catch_up=False).nudges

    # Assert
    assert nudges == (digest.stuck[0].nudge, digest.nudge)


def test_a_message_carrying_nothing_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="at least one"):
        NudgeMessage((), catch_up=False)
