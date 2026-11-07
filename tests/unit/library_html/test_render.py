from datetime import date

import pytest
from builders import an_item, an_outcome
from library_html_rig import (
    a_kept_snapshot,
    a_maximal_library,
    a_section_of,
    a_snapshot,
    appearing_order,
    parsed_markup,
)

from stash.domain import ItemType, Stage
from stash.library_html import LibraryEntry, render_library

TELEGRAM_DOCUMENT_LIMIT_BYTES = 45 * 1024 * 1024
LARGE_LIBRARY = 5000
SECTIONS_IN_LIBRARY = 4
SECTION_FIELDS = ("kept", "done_by_year", "want_to", "dropped")


def test_the_page_forbids_every_resource_load_except_inline_styles() -> None:
    # Execute
    page = render_library(a_snapshot())

    # Assert
    assert (
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; style-src 'unsafe-inline'\">" in page
    )


def test_the_page_asks_search_engines_not_to_index_it() -> None:
    # Execute
    page = render_library(a_snapshot())

    # Assert
    assert '<meta name="robots" content="noindex">' in page


def test_the_page_uses_only_inline_markup_with_no_script_or_external_resource_tags() -> None:
    # Setup
    snapshot = a_kept_snapshot(an_item(), [an_outcome()])

    # Execute
    tags = parsed_markup(render_library(snapshot)).tags

    # Assert
    assert tags & {"script", "link", "img", "iframe", "object"} == set()


def test_the_stylesheet_adapts_to_a_dark_colour_scheme_and_a_narrow_screen() -> None:
    # Execute
    page = render_library(a_snapshot())

    # Assert
    assert "prefers-color-scheme: dark" in page and 'name="viewport"' in page


def test_the_page_carries_the_given_title() -> None:
    # Execute
    page = render_library(a_snapshot(), title="Ana's stash")

    # Assert
    assert "<h1>Ana&#x27;s stash</h1>" in page


def test_kept_types_after_media_follow_in_the_order_the_types_are_declared() -> None:
    # Setup
    entries = {
        item_type: [LibraryEntry(an_item(id=item_type, title=f"t-{item_type}", kept=True), [])]
        for item_type in (ItemType.IDEA, ItemType.MEDIA, ItemType.RECIPE, ItemType.PLAN)
    }

    # Execute
    page = render_library(a_snapshot(kept=entries))

    # Assert
    assert appearing_order(page, ["t-idea", "t-media", "t-recipe", "t-plan"]) == [
        "t-recipe",
        "t-media",
        "t-idea",
        "t-plan",
    ]


def test_a_media_summary_is_shown_with_the_item() -> None:
    # Setup
    item = an_item(item_type=ItemType.MEDIA, kept=True)
    snapshot = a_snapshot(kept={item.item_type: [LibraryEntry(item, [], "A quiet heist film")]})

    # Execute
    page = render_library(snapshot)

    # Assert
    assert "A quiet heist film" in page


def test_the_notes_of_a_completion_are_shown() -> None:
    # Setup
    snapshot = a_kept_snapshot(an_item(), [an_outcome(notes="Better the second time")])

    # Execute
    page = render_library(snapshot)

    # Assert
    assert "Better the second time" in page


def test_an_unrated_completion_shows_no_stars() -> None:
    # Setup
    snapshot = a_kept_snapshot(an_item(), [an_outcome(rating=None)])

    # Execute
    page = render_library(snapshot)

    # Assert
    assert "★" not in page and "☆" not in page


def test_the_latest_completion_is_the_one_shown_when_an_item_was_done_twice() -> None:
    # Setup
    earlier = an_outcome(id="o1", takeaways=("First time",), completed_on=date(2025, 1, 1))
    later = an_outcome(id="o2", takeaways=("Second time",), completed_on=date(2026, 1, 1))

    # Execute
    page = render_library(a_kept_snapshot(an_item(), [later, earlier]))

    # Assert
    assert "Second time" in page and "First time" not in page


def test_a_dropped_item_without_a_reason_says_none_was_given() -> None:
    # Execute
    page = render_library(a_snapshot(dropped=[an_item(stage=Stage.DROPPED)]))

    # Assert
    assert "No reason given." in page


@pytest.mark.parametrize("field", SECTION_FIELDS)
def test_a_section_over_two_hundred_items_shows_the_first_two_hundred_and_counts_the_rest(
    field: str,
) -> None:
    # Execute
    page = render_library(a_section_of(201, field))

    # Assert
    assert page.count('<li class="entry">') == 200 and "…and 1 more" in page


@pytest.mark.parametrize("field", SECTION_FIELDS)
def test_a_section_of_exactly_two_hundred_items_says_nothing_about_more(field: str) -> None:
    # Execute
    page = render_library(a_section_of(200, field))

    # Assert
    assert "more</li>" not in page


def test_a_five_thousand_entry_library_of_maximum_length_text_stays_under_the_telegram_limit() -> (
    None
):
    # Setup
    snapshot = a_maximal_library(LARGE_LIBRARY // SECTIONS_IN_LIBRARY)

    # Execute
    page = render_library(snapshot)

    # Assert
    assert len(page.encode()) < TELEGRAM_DOCUMENT_LIMIT_BYTES


def test_a_five_thousand_entry_library_counts_what_each_section_leaves_out() -> None:
    # Setup
    snapshot = a_maximal_library(LARGE_LIBRARY // SECTIONS_IN_LIBRARY)

    # Execute
    page = render_library(snapshot)

    # Assert
    assert page.count("…and 1050 more") == SECTIONS_IN_LIBRARY
