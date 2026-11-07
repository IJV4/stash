from builders import MAX_LENGTH_ID
from nudge_builders import (
    SATURDAY_MORNING,
    SUNDAY_MORNING,
    a_date_reminder,
    a_follow_up,
    a_nudge_message,
    a_numbered_follow_up,
    a_numbered_step_reminder,
    a_planned_date_night,
    a_same_day_step,
    a_step_reminder,
    a_weekly_digest,
)

from stash.capture.nudge_replies import nudge_reply
from stash.capture.replies import Button
from stash.domain import Stage
from stash.nudges import DueNudge, FollowUp, StepReminder

SPEC_MAX_BUTTONS = 8
LONG_SUBJECT = "Reserve the restaurant table"


def button_count(*due: DueNudge) -> int:
    return sum(len(row) for row in nudge_reply(a_nudge_message(*due)).reply.buttons)


def test_a_step_reminder_alone_carries_a_bare_done_button_for_the_step() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder())).reply

    # Assert
    assert reply.buttons == ((Button("Done ✓", "stash:x:book-table"),),)


def test_a_follow_up_alone_carries_bare_done_and_didnt_happen_buttons_for_the_item() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_follow_up())).reply

    # Assert
    assert reply.buttons == (
        (
            Button("Done ✓", "stash:d:date-night"),
            Button("Didn't happen", "stash:h:date-night:20270213"),
        ),
    )


def test_a_date_reminder_carries_no_buttons() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_date_reminder())).reply

    # Assert
    assert reply.buttons == ()


def test_a_digest_carries_no_buttons() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_weekly_digest())).reply

    # Assert
    assert reply.buttons == ()


def test_a_step_reminder_beside_a_date_reminder_keeps_the_bare_done_button() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder(), a_date_reminder())).reply

    # Assert
    assert reply.buttons == ((Button("Done ✓", "stash:x:book-table"),),)


def test_a_follow_up_beside_the_digest_keeps_the_bare_labels() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_follow_up(), a_weekly_digest())).reply

    # Assert
    assert reply.buttons == (
        (
            Button("Done ✓", "stash:d:date-night"),
            Button("Didn't happen", "stash:h:date-night:20270213"),
        ),
    )


def test_with_several_rows_each_done_button_names_its_subject() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder(), a_follow_up())).reply

    # Assert
    assert [row[0].label for row in reply.buttons] == [
        "Done ✓ · Book the table",
        "Done ✓ · Date night",
    ]


def test_with_several_rows_the_didnt_happen_button_keeps_its_bare_label() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder(), a_follow_up())).reply

    # Assert
    assert reply.buttons[1][1] == Button("Didn't happen", "stash:h:date-night:20270213")


def test_a_subject_is_cut_to_twenty_four_characters_in_the_button_label() -> None:
    # Setup
    reminder = StepReminder(
        a_same_day_step(text=LONG_SUBJECT), a_planned_date_night(), SATURDAY_MORNING
    )

    # Execute
    reply = nudge_reply(a_nudge_message(reminder, a_follow_up())).reply

    # Assert
    assert reply.buttons[0][0].label == "Done ✓ · Reserve the restaurant t"


def test_a_subject_of_exactly_twenty_four_characters_is_not_cut() -> None:
    # Setup
    subject = "x" * 24
    reminder = StepReminder(a_same_day_step(text=subject), a_planned_date_night(), SATURDAY_MORNING)

    # Execute
    reply = nudge_reply(a_nudge_message(reminder, a_follow_up())).reply

    # Assert
    assert reply.buttons[0][0].label == f"Done ✓ · {subject}"


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


def test_a_row_that_fits_exactly_up_to_eight_buttons_is_kept() -> None:
    # Execute
    count = button_count(
        *(a_numbered_step_reminder(number) for number in range(6)), a_numbered_follow_up(10)
    )

    # Assert
    assert count == SPEC_MAX_BUTTONS


def test_callback_data_for_the_longest_allowed_ids_fits_the_telegram_limit() -> None:
    # Setup
    item = a_planned_date_night(id=MAX_LENGTH_ID)
    step = a_same_day_step(id=MAX_LENGTH_ID, item_id=MAX_LENGTH_ID)
    message = a_nudge_message(
        StepReminder(step, item, SATURDAY_MORNING), FollowUp(item, SUNDAY_MORNING)
    )

    # Execute
    reply = nudge_reply(message).reply

    # Assert
    assert max(len(button.data.encode()) for row in reply.buttons for button in row) <= 64


def test_a_follow_up_for_an_item_without_a_date_carries_only_the_done_button() -> None:
    # Execute
    reply = nudge_reply(
        a_nudge_message(
            FollowUp(a_planned_date_night(stage=Stage.WANT_TO, date=None), SUNDAY_MORNING)
        )
    ).reply

    # Assert
    assert reply.buttons == ((Button("Done ✓", "stash:d:date-night"),),)
