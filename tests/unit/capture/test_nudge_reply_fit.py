from nudge_builders import (
    SATURDAY,
    SATURDAY_MORNING,
    SUNDAY_DIGEST_TIME,
    a_date_reminder,
    a_follow_up,
    a_follow_up_whose_line_has,
    a_nudge_message,
    a_planned_date_night,
    a_same_day_step,
    a_step_reminder,
    a_stuck_book,
)

from stash.capture.nudge_replies import LINE_LIMIT, nudge_reply
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.nudges import DateReminder, FollowUp, StepReminder, StuckItem, WeeklyDigest

LINE_OF_THE_BOUNDARY_LENGTH = 272
LINES_THAT_FIT_WITHOUT_THE_HEADING = 15
LINES_THAT_FIT_WITH_THE_HEADING = 14
FULL_WIDTH_LINES_PER_MESSAGE = 13


def full_width_follow_ups(count: int) -> list[FollowUp]:
    return [a_follow_up_whose_line_has(LINE_LIMIT, number) for number in range(count)]


def long_date_reminders(count: int) -> list[DateReminder]:
    item = a_planned_date_night(title="x" * 2 * LINE_LIMIT)
    return [DateReminder(item, SATURDAY, SATURDAY_MORNING) for _ in range(count)]


def test_a_message_that_fits_is_shown_whole() -> None:
    # Setup
    message = a_nudge_message(a_step_reminder(), a_date_reminder(), a_follow_up())

    # Execute
    rendered = nudge_reply(message)

    # Assert
    assert rendered.shown == message


def test_a_line_longer_than_the_line_limit_is_cut_to_it() -> None:
    # Setup
    reminder = StepReminder(
        a_same_day_step(), a_planned_date_night(title="x" * 2 * LINE_LIMIT), SATURDAY_MORNING
    )

    # Execute
    rendered = nudge_reply(a_nudge_message(reminder))

    # Assert
    assert len(rendered.reply.text) == LINE_LIMIT


def test_a_step_text_with_a_line_break_cannot_start_a_line_of_its_own() -> None:
    # Setup
    reminder = StepReminder(
        a_same_day_step(text="Book\nHow was Evil?"), a_planned_date_night(), SATURDAY_MORNING
    )

    # Execute
    rendered = nudge_reply(a_nudge_message(reminder))

    # Assert
    assert len(rendered.reply.text.splitlines()) == 1


def test_an_item_title_with_a_line_break_cannot_start_a_line_of_its_own() -> None:
    # Setup
    follow_up = FollowUp(a_planned_date_night(title="Date\n📅 Forged"), SATURDAY_MORNING)

    # Execute
    rendered = nudge_reply(a_nudge_message(follow_up))

    # Assert
    assert rendered.reply.text == "How was Date 📅 Forged?"


def test_a_message_over_the_telegram_limit_shows_only_the_leading_nudges_that_fit() -> None:
    # Setup
    follow_ups = full_width_follow_ups(FULL_WIDTH_LINES_PER_MESSAGE + 1)

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups))

    # Assert
    assert rendered.shown.due == tuple(follow_ups[:FULL_WIDTH_LINES_PER_MESSAGE])


def test_the_text_of_a_message_over_the_telegram_limit_fits_it() -> None:
    # Setup
    follow_ups = full_width_follow_ups(FULL_WIDTH_LINES_PER_MESSAGE + 1)

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups))

    # Assert
    assert len(rendered.reply.text) <= TELEGRAM_TEXT_LIMIT


def test_the_shown_nudges_are_exactly_the_ones_the_text_has_lines_for() -> None:
    # Setup
    follow_ups = full_width_follow_ups(FULL_WIDTH_LINES_PER_MESSAGE + 1)

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups))

    # Assert
    assert len(rendered.reply.text.splitlines()) == len(rendered.shown.due)


def test_a_digest_that_does_not_fit_is_left_out_whole_and_not_cut_after_its_heading() -> None:
    # Setup
    follow_ups = full_width_follow_ups(FULL_WIDTH_LINES_PER_MESSAGE)
    long_stuck_title = a_stuck_book(title="x" * 2 * LINE_LIMIT)
    digest = WeeklyDigest(SUNDAY_DIGEST_TIME, (StuckItem(long_stuck_title, SUNDAY_DIGEST_TIME),))

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups, digest))

    # Assert
    assert rendered.shown.due == tuple(follow_ups)


def test_the_shown_part_of_a_catch_up_message_is_still_a_catch_up() -> None:
    # Setup
    follow_ups = full_width_follow_ups(FULL_WIDTH_LINES_PER_MESSAGE + 1)

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups, catch_up=True))

    # Assert
    assert rendered.shown.catch_up is True


def test_without_the_offline_heading_fifteen_long_lines_fit_and_a_sixteenth_does_not() -> None:
    # Setup
    follow_ups = [
        a_follow_up_whose_line_has(LINE_OF_THE_BOUNDARY_LENGTH, n)
        for n in range(LINES_THAT_FIT_WITHOUT_THE_HEADING + 1)
    ]

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups))

    # Assert
    assert len(rendered.shown.due) == LINES_THAT_FIT_WITHOUT_THE_HEADING


def test_the_offline_heading_counts_towards_the_telegram_limit() -> None:
    # Setup
    follow_ups = [
        a_follow_up_whose_line_has(LINE_OF_THE_BOUNDARY_LENGTH, n)
        for n in range(LINES_THAT_FIT_WITHOUT_THE_HEADING + 1)
    ]

    # Execute
    rendered = nudge_reply(a_nudge_message(*follow_ups, catch_up=True))

    # Assert
    assert len(rendered.shown.due) == LINES_THAT_FIT_WITH_THE_HEADING


def test_a_follow_up_that_does_not_fit_gets_no_buttons() -> None:
    # Setup
    reminders = long_date_reminders(LINES_THAT_FIT_WITH_THE_HEADING)

    # Execute
    rendered = nudge_reply(a_nudge_message(*reminders, a_follow_up()))

    # Assert
    assert rendered.reply.buttons == ()
