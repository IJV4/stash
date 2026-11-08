import pytest
from builders import fetched_outcome, stored_completion
from capture_builders import (
    COMPLETED_ITEM_ID,
    COMPLETED_OUTCOME_ID,
    INVALID_RATINGS,
    a_store_with_a_completed_item,
)
from capture_rig import a_fix_handler
from fakes.vanishing_item_store import VanishingItemStore

from stash.capture import gone

STORED_RATING = 4


def test_pressing_a_rating_for_an_unknown_outcome_answers_gone() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:r:ghost:3")

    # Assert
    assert reply == gone()


def test_a_rating_whose_item_was_deleted_right_after_saving_it_answers_gone() -> None:
    # Setup
    store = VanishingItemStore()
    stored_completion(store, COMPLETED_ITEM_ID)
    store.vanish_item_after_saving_outcome(COMPLETED_OUTCOME_ID)

    # Execute
    reply = a_fix_handler(store).apply(f"stash:r:{COMPLETED_OUTCOME_ID}:3")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("argument", INVALID_RATINGS)
def test_an_invalid_rating_answers_gone(argument: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:r:{COMPLETED_OUTCOME_ID}:{argument}")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("argument", INVALID_RATINGS)
def test_an_invalid_rating_changes_nothing(argument: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    a_fix_handler(store).apply(f"stash:r:{COMPLETED_OUTCOME_ID}:{argument}")

    # Assert
    assert fetched_outcome(store, COMPLETED_OUTCOME_ID).rating == STORED_RATING
