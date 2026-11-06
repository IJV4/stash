from nudge_builders import (
    SATURDAY,
    SATURDAY_MORNING,
    SUNDAY_DIGEST_TIME,
    a_date_reminder,
    a_follow_up,
    a_nudge_message,
    a_step_due_on,
    a_step_reminder,
    a_stuck_book,
    a_weekly_digest,
    an_undated_date_night,
)

from stash.capture.nudge_replies import nudge_reply
from stash.nudges import StepReminder, StuckItem, WeeklyDigest


def test_a_step_reminder_names_the_step_the_item_and_the_item_date() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder())).reply

    # Assert
    assert reply.text == "⏰ Book the table — for Date night (Sat Feb 13)"


def test_a_step_reminder_for_an_item_without_a_date_names_only_the_step_and_the_item() -> None:
    # Setup
    reminder = StepReminder(a_step_due_on(SATURDAY), an_undated_date_night(), SATURDAY_MORNING)

    # Execute
    reply = nudge_reply(a_nudge_message(reminder)).reply

    # Assert
    assert reply.text == "⏰ Book the table — for Date night"


def test_a_date_reminder_names_the_item_and_its_date() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_date_reminder())).reply

    # Assert
    assert reply.text == "📅 Date night (Sat Feb 13)"


def test_a_follow_up_asks_how_the_item_went() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_follow_up())).reply

    # Assert
    assert reply.text == "How was Date night?"


def test_a_digest_with_nothing_stuck_is_just_its_heading() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(WeeklyDigest(SUNDAY_DIGEST_TIME, ()))).reply

    # Assert
    assert reply.text == "🗞 Your weekly digest"


def test_a_digest_asks_about_each_stuck_item_under_its_heading() -> None:
    # Setup
    stuck = (
        StuckItem(a_stuck_book(), SUNDAY_DIGEST_TIME),
        StuckItem(a_stuck_book(id="b2", title="Dune"), SUNDAY_DIGEST_TIME),
    )

    # Execute
    reply = nudge_reply(a_nudge_message(WeeklyDigest(SUNDAY_DIGEST_TIME, stuck))).reply

    # Assert
    assert reply.text == (
        "🗞 Your weekly digest\n📖 How is Thinking in Systems going?\n📖 How is Dune going?"
    )


def test_a_message_lists_what_it_carries_one_line_each_in_order() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_step_reminder(), a_date_reminder(), a_follow_up())).reply

    # Assert
    assert reply.text.splitlines() == [
        "⏰ Book the table — for Date night (Sat Feb 13)",
        "📅 Date night (Sat Feb 13)",
        "How was Date night?",
    ]


def test_a_catch_up_message_starts_with_the_offline_heading() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_follow_up(), a_weekly_digest(), catch_up=True)).reply

    # Assert
    assert reply.text.splitlines() == [
        "While I was offline:",
        "How was Date night?",
        "🗞 Your weekly digest",
        "📖 How is Thinking in Systems going?",
    ]


def test_a_message_that_is_not_a_catch_up_has_no_offline_heading() -> None:
    # Execute
    reply = nudge_reply(a_nudge_message(a_follow_up())).reply

    # Assert
    assert "offline" not in reply.text
