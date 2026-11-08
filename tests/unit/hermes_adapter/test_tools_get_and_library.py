from builders import stored_completion
from fakes.store_factories import FreshStore
from tool_rig import (
    WANT_TO_ITEM,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
)

from stash.domain import ItemType


def a_kept_library() -> FreshStore:
    store = FreshStore()
    stored_completion(store, "dune", kept=True, item_type=ItemType.BOOK, title="Dune")
    stored_completion(store, "ramen", kept=True, item_type=ItemType.RECIPE, title="Ramen")
    stored_completion(store, "skipped", item_type=ItemType.BOOK, title="Not kept")
    return store


def test_library_with_a_limit_over_the_maximum_answers_an_error() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(a_kept_library()).library({"limit": 51}))

    # Assert
    assert answer == {"error": "limit must be between 1 and 50"}


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
