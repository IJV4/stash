import pytest
from digest_builders import (
    SAIL_REASON,
    a_digest_with,
    a_step_entry,
    an_item_entry,
    some_picks,
    some_stuck,
    some_want_tos,
)
from nudge_builders import STUCK_BOOK_LINE, a_stuck_book

from stash.capture.digest_replies import DIGEST_HEADER, render_digest
from stash.capture.wording import LINE_LIMIT
from stash.nudges import WeeklyDigest

FULL_DIGEST_TEXT = "\n".join(
    [
        "🗞 Your weekly digest",
        "🆕 New this week",
        "• Pasta",
        "🕰 Forgotten",
        "• Sail",
        "📅 Coming up",
        "• Sat Feb 13 — Date night",
        "📖 How is Thinking in Systems going?",
        "💡 Ideas for this week",
        f"• Pick 0 — {SAIL_REASON}",
    ]
)


def a_full_digest() -> WeeklyDigest:
    return a_digest_with(
        new_items=some_want_tos(1, "pasta", title="Pasta"),
        forgotten=some_want_tos(1, "sail", title="Sail"),
        upcoming=[an_item_entry()],
        picks=some_picks(1),
        stuck=[a_stuck_book()],
    )


def test_a_digest_with_nothing_in_it_is_its_header_alone() -> None:
    # Execute
    reply = render_digest(a_digest_with())

    # Assert
    assert reply.text == DIGEST_HEADER


def test_the_header_of_the_digest_is_the_weekly_digest_line() -> None:
    # Assert
    assert DIGEST_HEADER == "🗞 Your weekly digest"


def test_a_digest_with_every_section_lists_them_in_order_under_their_headings() -> None:
    # Execute
    reply = render_digest(a_full_digest())

    # Assert
    assert reply.text == FULL_DIGEST_TEXT


def test_the_digest_reply_carries_no_buttons() -> None:
    # Execute
    reply = render_digest(a_full_digest())

    # Assert
    assert reply.buttons == ()


def test_the_digest_text_has_no_blank_line() -> None:
    # Execute
    reply = render_digest(a_full_digest())

    # Assert
    assert "" not in reply.text.split("\n")


@pytest.mark.parametrize(
    ("heading", "without"),
    [
        ("🆕 New this week", {"new_items": ()}),
        ("🕰 Forgotten", {"forgotten": ()}),
        ("📅 Coming up", {"upcoming": ()}),
        ("💡 Ideas for this week", {"picks": ()}),
    ],
)
def test_a_section_with_nothing_in_it_is_left_out_with_its_heading(
    heading: str, without: dict[str, tuple[()]]
) -> None:
    # Setup
    fields = {
        "new_items": some_want_tos(1),
        "forgotten": some_want_tos(1),
        "upcoming": [an_item_entry()],
        "picks": some_picks(1),
        **without,
    }

    # Execute
    reply = render_digest(a_digest_with(**fields))

    # Assert
    assert heading not in reply.text


def test_a_digest_with_stuck_items_and_nothing_else_is_the_header_and_the_stuck_lines() -> None:
    # Execute
    reply = render_digest(a_digest_with(stuck=[a_stuck_book()]))

    # Assert
    assert reply.text == f"{DIGEST_HEADER}\n{STUCK_BOOK_LINE}"


def test_a_coming_up_step_names_its_text_and_its_item() -> None:
    # Execute
    reply = render_digest(a_digest_with(upcoming=[a_step_entry()]))

    # Assert
    assert reply.text.splitlines()[-1] == "• Fri Feb 12 — Book the table (Date night)"


def test_a_coming_up_item_names_its_title_after_its_day() -> None:
    # Execute
    reply = render_digest(a_digest_with(upcoming=[an_item_entry()]))

    # Assert
    assert reply.text.splitlines()[-1] == "• Sat Feb 13 — Date night"


def test_a_suggestion_reads_as_its_title_and_its_reason() -> None:
    # Execute
    reply = render_digest(a_digest_with(picks=some_picks(1)))

    # Assert
    assert reply.text.splitlines()[-1] == f"• Pick 0 — {SAIL_REASON}"


def test_a_title_with_line_breaks_cannot_start_a_line_of_its_own() -> None:
    # Setup
    forgotten = some_want_tos(1, title="Sail\n📖 How is Forged going?")

    # Execute
    reply = render_digest(a_digest_with(forgotten=forgotten))

    # Assert
    assert reply.text.splitlines()[-1] == "• Sail 📖 How is Forged going?"


@pytest.mark.parametrize(
    "fields",
    [
        {"new_items": some_want_tos(1, title="x" * 400)},
        {"forgotten": some_want_tos(1, title="x" * 400)},
        {"upcoming": [an_item_entry(title="x" * 400)]},
        {"upcoming": [a_step_entry(text="x" * 200, title="y" * 200)]},
        {"stuck": some_stuck(1, title="x" * 400)},
        {"picks": some_picks(1, title="x" * 400)},
    ],
    ids=["new", "forgotten", "upcoming-item", "upcoming-step", "stuck", "picks"],
)
def test_every_kind_of_line_is_cut_to_the_line_limit(fields: dict[str, object]) -> None:
    # Execute
    reply = render_digest(a_digest_with(**fields))

    # Assert
    assert max(len(line) for line in reply.text.splitlines()) == LINE_LIMIT
