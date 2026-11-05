from builders import an_outcome, days_after, stored_completion, stored_item
from fakes.memory_store import MemoryStore
from tool_rig import (
    DONE_ITEM,
    DONE_ITEM_OUTCOME,
    WANT_TO_ITEM,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
)

from stash.domain import ItemType, Stage


def a_kept_library() -> MemoryStore:
    store = MemoryStore()
    stored_completion(store, "dune", kept=True, item_type=ItemType.BOOK, title="Dune")
    stored_completion(store, "ramen", kept=True, item_type=ItemType.RECIPE, title="Ramen")
    stored_completion(store, "skipped", item_type=ItemType.BOOK, title="Not kept")
    return store


def test_library_lists_kept_items_with_their_last_rating_and_finishing_day() -> None:
    # Setup
    tools = lifecycle_tools_over(a_kept_library())

    # Execute
    answer = answer_of(tools.library({"item_type": "book"}))

    # Assert
    assert answer == {
        "items": [
            {
                "id": "dune",
                "type": "book",
                "title": "Dune",
                "stage": "done",
                "date": None,
                "rating": 4,
                "completed_on": "2026-11-02",
            }
        ]
    }


def test_library_without_a_type_lists_every_kept_item() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_kept_library()).library({}))

    # Assert
    assert sorted(entry["id"] for entry in answer["items"]) == ["dune", "ramen"]


def test_library_honours_the_limit() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_kept_library()).library({"limit": 1}))

    # Assert
    assert len(answer["items"]) == 1


def test_library_leaves_the_rating_empty_for_an_item_whose_outcome_has_none() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="k1", stage=Stage.DONE, kept=True)
    store.add_outcome(an_outcome(id="o1", item_id="k1", rating=None))

    # Execute
    answer = answer_of(lifecycle_tools_over(store).library({}))

    # Assert
    assert answer["items"][0]["rating"] is None


def test_library_with_a_limit_over_the_maximum_answers_an_error() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_kept_library()).library({"limit": 51}))

    # Assert
    assert answer == {"error": "limit must be between 1 and 50"}


def test_get_answers_the_item_its_outcomes_and_its_children() -> None:
    # Setup
    store = MemoryStore()
    stored_item(
        store,
        id="m1",
        item_type=ItemType.MEDIA,
        title="Kurzgesagt: Black holes",
        stage=Stage.DONE,
        source_url="https://example.com/watch?v=1",
        note="saw it on a list",
        details={"link_title": "Black holes", "uploader": "Kurzgesagt", "duration": "11:02"},
        kept=True,
    )
    store.add_outcome(an_outcome(id="o1", item_id="m1", takeaways=("Event horizons", "Spaghetti")))
    stored_item(store, id="m2", title="Part two", parent_id="m1")

    # Execute
    answer = answer_of(lifecycle_tools_over(store).get({"item_id": "m1"}))

    # Assert
    assert answer == {
        "item": {
            "id": "m1",
            "type": "media",
            "title": "Kurzgesagt: Black holes",
            "stage": "done",
            "date": None,
            "kept": True,
            "in_library": True,
            "parent_id": None,
            "drop_reason": None,
            "source_url": "https://example.com/watch?v=1",
            "note": "saw it on a list",
            "details": {"link_title": "Black holes", "uploader": "Kurzgesagt", "duration": "11:02"},
        },
        "outcomes": [
            {
                "id": "o1",
                "completed_on": "2026-11-02",
                "rating": 4,
                "notes": "Great",
                "takeaways": ["Event horizons", "Spaghetti"],
            }
        ],
        "children": [
            {"id": "m2", "type": "place", "title": "Part two", "stage": "inbox", "date": None}
        ],
    }


def test_get_lists_the_outcomes_oldest_first() -> None:
    # Setup
    store = a_tool_store()
    store.add_outcome(an_outcome(id="later", item_id=DONE_ITEM, completed_on=days_after(3)))

    # Execute
    answer = answer_of(lifecycle_tools_over(store).get({"item_id": DONE_ITEM}))

    # Assert
    assert [outcome["id"] for outcome in answer["outcomes"]] == [DONE_ITEM_OUTCOME, "later"]


def test_get_shows_why_a_dropped_item_was_dropped() -> None:
    # Setup
    store = a_tool_store()
    lifecycle_tools_over(store).set_stage(
        {"item_id": WANT_TO_ITEM, "stage": "dropped", "reason": "too long"}
    )

    # Execute
    answer = answer_of(lifecycle_tools_over(store).get({"item_id": WANT_TO_ITEM}))

    # Assert
    assert answer["item"]["drop_reason"] == "too long"


def test_getting_an_unknown_item_answers_an_error_naming_it() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_tool_store()).get({"item_id": "zz"}))

    # Assert
    assert answer == {"error": "no item 'zz'"}
