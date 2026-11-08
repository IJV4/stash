from datetime import date, datetime

import pytest
from builders import (
    EARLY_MORNING_PLUS_FIVE,
    LATE_EVENING_MINUS_FIVE,
    stored_completion,
    stored_item,
)
from fakes.store_factories import FreshStore
from library_html_rig import LOCAL_NOW, appearing_order, rendered, store_of_kept_items

from stash.domain import ItemType, Stage

SECTIONS = ("Kept", "Done", "Want to", "Dropped")
WANT_TO_ITEMS_OVER_THE_CAP = 201
DROPPED_MARKER = '<section id="dropped">'


def test_kept_items_are_grouped_by_type_with_recipes_then_books_then_places() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "pl", title="Ramen bar", item_type=ItemType.PLACE, kept=True)
    stored_completion(store, "bk", title="Dune", item_type=ItemType.BOOK, kept=True)
    stored_completion(store, "rc", title="Carbonara", item_type=ItemType.RECIPE, kept=True)

    # Execute
    page = rendered(store)

    # Assert
    assert appearing_order(page, ["Ramen bar", "Dune", "Carbonara"]) == [
        "Carbonara",
        "Dune",
        "Ramen bar",
    ]


def test_kept_items_show_the_takeaways_recorded_when_they_were_completed() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "bk", item_type=ItemType.BOOK, kept=True)

    # Execute
    page = rendered(store)

    # Assert
    assert "Salt early" in page


def test_done_items_are_grouped_by_year_with_the_newest_year_first() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "old", completed_on=date(2025, 3, 1))
    stored_completion(store, "new", completed_on=date(2026, 5, 1))

    # Execute
    page = rendered(store)

    # Assert
    assert appearing_order(page, ["2025 (1)", "2026 (1)"]) == ["2026 (1)", "2025 (1)"]


def test_a_done_item_shows_its_star_rating() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "film")

    # Execute
    page = rendered(store)

    # Assert
    assert "★★★★☆" in page


def test_a_done_item_shows_the_day_it_was_completed() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "film", completed_on=date(2026, 3, 14))

    # Execute
    page = rendered(store)

    # Assert
    assert "2026-03-14" in page


def test_the_sections_run_kept_then_done_then_want_to_then_dropped() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="wish", stage=Stage.WANT_TO)
    stored_item(store, id="gone", stage=Stage.DROPPED)
    stored_completion(store, "bk", kept=True)
    headings = ["<h2>Dropped", "<h2>Want to", "<h2>Done", "<h2>Kept"]

    # Execute
    page = rendered(store)

    # Assert
    assert appearing_order(page, headings) == ["<h2>Kept", "<h2>Done", "<h2>Want to", "<h2>Dropped"]


def test_want_to_items_are_grouped_by_type() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="a", title="Ramen bar", stage=Stage.WANT_TO, item_type=ItemType.PLACE)
    stored_item(store, id="b", title="Dune", stage=Stage.WANT_TO, item_type=ItemType.BOOK)
    stored_item(store, id="c", title="Carbonara", stage=Stage.WANT_TO, item_type=ItemType.RECIPE)

    # Execute
    page = rendered(store)

    # Assert
    assert appearing_order(page, ["Ramen bar", "Dune", "Carbonara"]) == [
        "Carbonara",
        "Dune",
        "Ramen bar",
    ]


def test_dropped_items_appear_inside_a_collapsed_section_with_their_reason() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="gone", stage=Stage.DROPPED, drop_reason="lost interest")

    # Execute
    page = rendered(store)

    # Assert
    assert "lost interest" in page.split("<details>")[1].split("</details>")[0]


def test_a_dropped_item_that_was_once_completed_is_not_listed_under_done() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "gone", title="Old plan", stage=Stage.DROPPED)

    # Execute
    before_dropped, from_dropped = rendered(store).split(DROPPED_MARKER)

    # Assert
    assert "Old plan" not in before_dropped and "Old plan" in from_dropped


def test_the_header_counts_each_section() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="wish", stage=Stage.WANT_TO)
    stored_item(store, id="gone", stage=Stage.DROPPED)
    stored_completion(store, "bk", kept=True)

    # Execute
    page = rendered(store)

    # Assert
    assert "1 kept · 1 done · 1 want to · 1 dropped" in page


def test_the_header_shows_the_generated_time_in_the_local_timezone() -> None:
    # Execute
    page = rendered(FreshStore(), now=LOCAL_NOW)

    # Assert
    assert "Generated 2026-11-07 09:30 PST" in page


def test_an_empty_library_says_there_is_nothing_here_yet() -> None:
    # Execute
    page = rendered(FreshStore())

    # Assert
    assert page.count("Nothing here yet.") == len(SECTIONS)


def test_people_linked_to_an_item_never_appear() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "gift", kept=True, people=("Ana Garcia",))

    # Execute
    page = rendered(store)

    # Assert
    assert "Ana Garcia" not in page


def test_a_library_larger_than_one_store_page_is_counted_in_full() -> None:
    # Setup
    store = store_of_kept_items(5)

    # Execute
    page = rendered(store, page_size=2)

    # Assert
    assert "5 kept · 5 done" in page


@pytest.mark.parametrize("now", [EARLY_MORNING_PLUS_FIVE, LATE_EVENING_MINUS_FIVE])
def test_an_item_completed_on_the_local_date_is_listed_under_done_whatever_the_utc_date(
    now: datetime,
) -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "film", title="Local day film", completed_on=now.date())

    # Execute
    page = rendered(store, now=now)

    # Assert
    assert "Local day film" in page.split('<section id="done">')[1].split(DROPPED_MARKER)[0]


def test_a_library_with_two_hundred_and_one_want_to_items_counts_the_one_left_out() -> None:
    # Setup
    store = FreshStore()
    for number in range(WANT_TO_ITEMS_OVER_THE_CAP):
        stored_item(store, id=f"w{number}", stage=Stage.WANT_TO)

    # Execute
    page = rendered(store)

    # Assert
    assert "…and 1 more" in page


def test_a_kept_media_item_without_media_notes_renders_no_summary_paragraph() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "heat", title="Heat", item_type=ItemType.MEDIA, kept=True)

    # Execute
    page = rendered(store)

    # Assert
    assert "Heat" in page and '<p class="summary">' not in page
