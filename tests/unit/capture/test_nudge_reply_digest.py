from digest_builders import (
    a_digest_with,
    some_item_entries,
    some_picks,
    some_stuck,
    some_want_tos,
)
from nudge_builders import a_follow_up_whose_line_has, a_nudge_message

from stash.capture.digest_replies import render_digest
from stash.capture.nudge_replies import nudge_reply
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.capture.wording import LINE_LIMIT
from stash.domain import NudgeKind
from stash.nudges import FollowUp, WeeklyDigest

FULL_WIDTH_LINES_BEFORE_THE_DIGEST = 13


def a_filled_digest() -> WeeklyDigest:
    return a_digest_with(
        new_items=some_want_tos(2, "new"),
        forgotten=some_want_tos(1, "old", title="Learn to sail"),
        upcoming=some_item_entries(2),
        picks=some_picks(1),
        stuck=some_stuck(1),
    )


def a_digest_that_needs_a_line_of_its_own() -> WeeklyDigest:
    return a_digest_with(forgotten=some_want_tos(1, "old", title="x" * 2 * LINE_LIMIT))


def full_width_follow_ups() -> list[FollowUp]:
    return [
        a_follow_up_whose_line_has(LINE_LIMIT, number)
        for number in range(FULL_WIDTH_LINES_BEFORE_THE_DIGEST)
    ]


def test_a_filled_digest_alone_reads_exactly_as_the_digest_reply() -> None:
    # Setup
    digest = a_filled_digest()

    # Execute
    reply = nudge_reply(a_nudge_message(digest)).reply

    # Assert
    assert reply.text == render_digest(digest).text


def test_a_filled_digest_after_a_reminder_follows_the_reminder_line_by_line() -> None:
    # Setup
    digest = a_filled_digest()
    follow_up = a_follow_up_whose_line_has(40)

    # Execute
    reply = nudge_reply(a_nudge_message(follow_up, digest)).reply

    # Assert
    assert reply.text.splitlines()[1:] == render_digest(digest).text.splitlines()


def test_a_filled_digest_that_fits_beside_the_reminders_before_it_is_shown_whole() -> None:
    # Setup
    message = a_nudge_message(a_follow_up_whose_line_has(40), a_filled_digest())

    # Execute
    rendered = nudge_reply(message)

    # Assert
    assert rendered.shown == message


def test_a_filled_digest_that_does_not_fit_beside_the_reminders_is_left_out_whole() -> None:
    # Setup
    follow_ups = full_width_follow_ups()
    message = a_nudge_message(*follow_ups, a_digest_that_needs_a_line_of_its_own())

    # Execute
    rendered = nudge_reply(message)

    # Assert
    assert rendered.shown.due == tuple(follow_ups)


def test_nothing_of_a_digest_that_was_left_out_is_among_the_nudges_to_mark_sent() -> None:
    # Setup
    message = a_nudge_message(*full_width_follow_ups(), a_digest_that_needs_a_line_of_its_own())

    # Execute
    rendered = nudge_reply(message)

    # Assert
    assert {nudge.kind for nudge in rendered.shown.nudges} == {NudgeKind.FOLLOWUP}


def test_a_digest_that_is_all_the_message_has_is_shown_even_when_it_is_the_longest_it_can_be() -> (
    None
):
    # Setup
    digest = a_digest_with(
        new_items=some_want_tos(9, "new", title="x" * 2 * LINE_LIMIT),
        forgotten=some_want_tos(3, "old", title="x" * 2 * LINE_LIMIT),
        upcoming=some_item_entries(9, title="x" * 2 * LINE_LIMIT),
        picks=some_picks(3, title="x" * 2 * LINE_LIMIT),
        stuck=some_stuck(12, title="x" * 2 * LINE_LIMIT),
    )

    # Execute
    reply = nudge_reply(a_nudge_message(digest)).reply

    # Assert
    assert len(reply.text) <= TELEGRAM_TEXT_LIMIT
