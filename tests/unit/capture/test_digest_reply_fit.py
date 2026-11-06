from collections.abc import Callable
from itertools import takewhile

from digest_builders import (
    a_digest_with,
    some_item_entries,
    some_picks,
    some_stuck,
    some_want_tos,
)

from stash.capture.digest_replies import render_digest
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.capture.wording import LINE_LIMIT
from stash.domain import Item
from stash.domain.item import TITLE_LIMIT
from stash.nudges import WeeklyDigest

LONGEST_TITLE = "t" * TITLE_LIMIT
OVERSIZE = "x" * (2 * LINE_LIMIT)
NEW_HEADING = "🆕 New this week"
UPCOMING_HEADING = "📅 Coming up"
PICKS_HEADING = "💡 Ideas for this week"
FORGOTTEN_HEADING = "🕰 Forgotten"
SECTION_STARTS = ("🆕", "🕰", "📅", "📖", "💡")
FORGOTTEN_LINES = 3
STUCK_LINES = 10
STUCK_LINES_LEAVING_ROOM_FOR_TWO_PICKS = 8


def long_forgotten() -> tuple[Item, ...]:
    return some_want_tos(FORGOTTEN_LINES, "old", title=OVERSIZE)


def long_stuck(count: int = STUCK_LINES) -> tuple[Item, ...]:
    return some_stuck(count, title=OVERSIZE)


def lines_of(digest: WeeklyDigest) -> list[str]:
    return render_digest(digest).text.splitlines()


def section(heading: str, lines: list[str]) -> list[str]:
    after_heading = lines[lines.index(heading) + 1 :]
    return [heading, *takewhile(lambda line: not line.startswith(SECTION_STARTS), after_heading)]


def digest_filling_the_limit_exactly(with_title_length: Callable[[int], WeeklyDigest]) -> int:
    short = len(render_digest(with_title_length(1)).text)
    return 1 + TELEGRAM_TEXT_LIMIT - short


def new_item_filling(title_length: int) -> WeeklyDigest:
    return a_digest_with(
        new_items=some_want_tos(1, "new", title="n" * title_length),
        forgotten=long_forgotten(),
        stuck=long_stuck(),
    )


def test_text_of_exactly_the_telegram_limit_is_shown_whole() -> None:
    # Setup
    title_length = digest_filling_the_limit_exactly(new_item_filling)

    # Execute
    reply = render_digest(new_item_filling(title_length))

    # Assert
    assert len(reply.text) == TELEGRAM_TEXT_LIMIT


def test_text_one_character_over_the_telegram_limit_shows_one_new_item_fewer() -> None:
    # Setup
    title_length = digest_filling_the_limit_exactly(new_item_filling) + 1

    # Execute
    lines = lines_of(new_item_filling(title_length))

    # Assert
    assert section(NEW_HEADING, lines) == [NEW_HEADING, "…and 1 more"]


def test_suggestions_lose_lines_before_new_items_do() -> None:
    # Setup
    digest = a_digest_with(
        new_items=some_want_tos(2, "new"),
        forgotten=long_forgotten(),
        stuck=long_stuck(),
        picks=some_picks(3, title=OVERSIZE),
    )

    # Execute
    lines = lines_of(digest)

    # Assert
    assert (
        section(NEW_HEADING, lines),
        section(PICKS_HEADING, lines),
    ) == ([NEW_HEADING, "• New 0", "• New 1"], [PICKS_HEADING, "…and 3 more"])


def test_suggestions_keep_as_many_lines_as_fit() -> None:
    # Setup
    digest = a_digest_with(
        forgotten=long_forgotten(),
        stuck=long_stuck(STUCK_LINES_LEAVING_ROOM_FOR_TWO_PICKS),
        picks=some_picks(3, title=OVERSIZE),
    )

    # Execute
    picks = section(PICKS_HEADING, lines_of(digest))

    # Assert
    assert (len(picks), picks[-1]) == (1 + 2 + 1, "…and 1 more")


def test_new_items_lose_lines_once_the_suggestions_have_none_left_to_lose() -> None:
    # Setup
    digest = a_digest_with(
        new_items=some_want_tos(5, "new", title=OVERSIZE),
        forgotten=long_forgotten(),
        upcoming=some_item_entries(3),
        stuck=long_stuck(),
        picks=some_picks(3),
    )

    # Execute
    lines = lines_of(digest)

    # Assert
    assert (
        section(NEW_HEADING, lines),
        section(PICKS_HEADING, lines),
    ) == ([NEW_HEADING, "…and 5 more"], [PICKS_HEADING, "…and 3 more"])


def test_coming_up_keeps_its_lines_while_suggestions_and_new_items_can_still_give_way() -> None:
    # Setup
    digest = a_digest_with(
        new_items=some_want_tos(5, "new", title=OVERSIZE),
        forgotten=long_forgotten(),
        upcoming=some_item_entries(3),
        stuck=long_stuck(),
        picks=some_picks(3),
    )

    # Execute
    upcoming = section(UPCOMING_HEADING, lines_of(digest))

    # Assert
    assert len(upcoming) == 1 + 3


def test_coming_up_loses_lines_last() -> None:
    # Setup
    digest = a_digest_with(
        new_items=some_want_tos(3, "new"),
        forgotten=long_forgotten(),
        upcoming=some_item_entries(8, title=OVERSIZE),
        stuck=long_stuck(),
        picks=some_picks(3),
    )

    # Execute
    lines = lines_of(digest)

    # Assert
    assert (
        section(NEW_HEADING, lines),
        section(UPCOMING_HEADING, lines),
        section(PICKS_HEADING, lines),
    ) == (
        [NEW_HEADING, "…and 3 more"],
        [UPCOMING_HEADING, "…and 8 more"],
        [PICKS_HEADING, "…and 3 more"],
    )


def worst_case_digest() -> WeeklyDigest:
    return a_digest_with(
        new_items=some_want_tos(20, "new", title=OVERSIZE),
        forgotten=long_forgotten(),
        upcoming=some_item_entries(20, title=OVERSIZE),
        stuck=long_stuck(20),
        picks=some_picks(3, title=OVERSIZE),
    )


def test_even_the_worst_case_digest_fits_the_telegram_limit() -> None:
    # Execute
    reply = render_digest(worst_case_digest())

    # Assert
    assert len(reply.text) <= TELEGRAM_TEXT_LIMIT


def test_the_worst_case_digest_still_lists_every_forgotten_item() -> None:
    # Execute
    lines = lines_of(worst_case_digest())

    # Assert
    assert len(section(FORGOTTEN_HEADING, lines)) == 1 + FORGOTTEN_LINES


def test_the_worst_case_digest_still_lists_every_stuck_line_up_to_the_stuck_cap() -> None:
    # Execute
    lines = lines_of(worst_case_digest())

    # Assert
    assert sum(line.startswith("📖 How is") for line in lines) == STUCK_LINES


def digest_with_every_section_at_its_cap_and_the_longest_titles() -> WeeklyDigest:
    return a_digest_with(
        new_items=some_want_tos(5, "new", title=LONGEST_TITLE),
        forgotten=some_want_tos(FORGOTTEN_LINES, "old", title=LONGEST_TITLE),
        upcoming=some_item_entries(8, title=LONGEST_TITLE),
        stuck=some_stuck(STUCK_LINES, title=LONGEST_TITLE),
        picks=some_picks(3, title=LONGEST_TITLE),
    )


def test_a_digest_with_every_section_at_its_cap_and_the_longest_titles_fits_the_limit() -> None:
    # Execute
    reply = render_digest(digest_with_every_section_at_its_cap_and_the_longest_titles())

    # Assert
    assert len(reply.text) <= TELEGRAM_TEXT_LIMIT


def test_that_digest_hides_no_forgotten_and_no_stuck_line() -> None:
    # Execute
    lines = lines_of(digest_with_every_section_at_its_cap_and_the_longest_titles())

    # Assert
    assert (
        len(section(FORGOTTEN_HEADING, lines)) - 1,
        sum(line.startswith("📖 How is") for line in lines),
    ) == (FORGOTTEN_LINES, STUCK_LINES)
