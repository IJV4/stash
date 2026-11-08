from nudge_builders import (
    SUNDAY_MORNING,
    a_nudge_message,
    a_numbered_follow_up,
    a_numbered_step_reminder,
    a_planned_date_night,
)

from stash.capture.nudge_replies import nudge_reply
from stash.capture.replies import Button
from stash.domain import Stage
from stash.nudges import DueNudge, FollowUp

SPEC_MAX_BUTTONS = 8


def button_count(*due: DueNudge) -> int:
    return sum(len(row) for row in nudge_reply(a_nudge_message(*due)).reply.buttons)


def test_five_step_reminders_and_two_follow_ups_leave_out_the_second_follow_up_row() -> None:
    # Setup
    reminders = [a_numbered_step_reminder(number) for number in range(5)]
    follow_ups = [a_numbered_follow_up(10), a_numbered_follow_up(11)]

    # Execute
    reply = nudge_reply(a_nudge_message(*reminders, *follow_ups)).reply

    # Assert
    assert [row[0].data for row in reply.buttons][-2:] == ["stash:x:step-4", "stash:d:item-10"]


def test_no_row_after_the_first_that_does_not_fit_gets_buttons_even_if_it_would_fit_alone() -> None:
    # Setup
    reminders = [a_numbered_step_reminder(number) for number in range(7)]
    message = a_nudge_message(*reminders, a_numbered_follow_up(10), a_numbered_step_reminder(8))

    # Execute
    reply = nudge_reply(message).reply

    # Assert
    assert [row[0].data for row in reply.buttons] == [f"stash:x:step-{n}" for n in range(7)]


def test_a_left_out_rows_reminder_stays_in_the_text() -> None:
    # Setup
    reminders = [a_numbered_step_reminder(number) for number in range(5)]
    follow_ups = [a_numbered_follow_up(10), a_numbered_follow_up(11)]

    # Execute
    reply = nudge_reply(a_nudge_message(*reminders, *follow_ups)).reply

    # Assert
    assert reply.text.splitlines()[-1] == "How was Event 11?"


def test_a_message_never_carries_more_than_eight_buttons() -> None:
    # Execute
    count = button_count(*(a_numbered_step_reminder(number) for number in range(12)))

    # Assert
    assert count == SPEC_MAX_BUTTONS


def test_a_follow_up_for_an_item_without_a_date_carries_only_the_done_button() -> None:
    # Execute
    reply = nudge_reply(
        a_nudge_message(
            FollowUp(a_planned_date_night(stage=Stage.WANT_TO, date=None), SUNDAY_MORNING)
        )
    ).reply

    # Assert
    assert reply.buttons == ((Button("Done ✓", "stash:d:date-night"),),)
