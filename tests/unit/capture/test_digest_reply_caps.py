import pytest
from digest_builders import a_digest_with, some_item_entries, some_picks, some_stuck, some_want_tos

from stash.capture.digest_replies import WAITING_LINE, render_digest
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, telegram_length

AFTER_HEADER_AND_HEADING = 2
AFTER_HEADER = 1


def body_after(heading_lines: int, digest_text: str) -> list[str]:
    return digest_text.splitlines()[heading_lines:]


@pytest.mark.parametrize(("count", "hidden"), [(1, 0), (5, 0), (6, 1), (9, 4)])
def test_the_new_section_lists_five_items_and_counts_the_rest(count: int, hidden: int) -> None:
    # Setup
    digest = a_digest_with(new_items=some_want_tos(count, "new"))
    shown = [f"• New {n}" for n in range(min(count, 5))]

    # Execute
    reply = render_digest(digest)

    # Assert
    assert body_after(AFTER_HEADER_AND_HEADING, reply.text) == [
        *shown,
        *([f"…and {hidden} more"] if hidden else []),
    ]


@pytest.mark.parametrize(("count", "hidden"), [(1, 0), (8, 0), (9, 1), (12, 4)])
def test_the_coming_up_section_lists_eight_entries_and_counts_the_rest(
    count: int, hidden: int
) -> None:
    # Setup
    digest = a_digest_with(upcoming=some_item_entries(count))
    shown = [f"• Sat Feb 13 — Event {n}" for n in range(min(count, 8))]

    # Execute
    reply = render_digest(digest)

    # Assert
    assert body_after(AFTER_HEADER_AND_HEADING, reply.text) == [
        *shown,
        *([f"…and {hidden} more"] if hidden else []),
    ]


@pytest.mark.parametrize(("count", "hidden"), [(1, 0), (10, 0), (11, 1), (14, 4)])
def test_the_stuck_lines_are_ten_and_the_rest_are_counted(count: int, hidden: int) -> None:
    # Setup
    digest = a_digest_with(stuck=some_stuck(count))
    shown = [f"📖 How is Book {n} going?" for n in range(min(count, 10))]

    # Execute
    reply = render_digest(digest)

    # Assert
    assert body_after(AFTER_HEADER, reply.text) == [
        *shown,
        *([f"…and {hidden} more"] if hidden else []),
    ]


def test_the_forgotten_section_lists_all_three_items_without_a_count() -> None:
    # Setup
    digest = a_digest_with(forgotten=some_want_tos(3, "old"))

    # Execute
    reply = render_digest(digest)

    # Assert
    assert body_after(AFTER_HEADER_AND_HEADING, reply.text) == ["• Old 0", "• Old 1", "• Old 2"]


def test_the_suggestions_section_lists_all_three_picks_without_a_count() -> None:
    # Setup
    digest = a_digest_with(picks=some_picks(3))

    # Execute
    reply = render_digest(digest)

    # Assert
    assert len(body_after(AFTER_HEADER_AND_HEADING, reply.text)) == 3


def test_the_waiting_line_survives_a_digest_trimmed_to_fit() -> None:
    # Setup
    long_title = "T" * 300
    digest = a_digest_with(
        new_items=some_want_tos(5, "new", long_title),
        upcoming=some_item_entries(8, long_title),
        picks=some_picks(3, long_title),
        waiting_captures=4,
    )

    # Execute
    text = render_digest(digest).text

    # Assert
    assert (WAITING_LINE.format(count=4) in text, telegram_length(text) <= TELEGRAM_TEXT_LIMIT) == (
        True,
        True,
    )
