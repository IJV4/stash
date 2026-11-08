import pytest
from builders import fetched_item
from capture_builders import (
    COMPLETED_ITEM_ID,
    INVALID_KEEP_CHOICES,
    a_store_with_a_completed_item,
    store_with_filed_item,
)
from capture_rig import a_fix_handler
from lifecycle_rig import a_lifecycle

from stash.capture import gone
from stash.capture.replies import refused
from stash.lifecycle.errors import LifecycleRefused


def test_keeping_an_item_that_is_no_longer_done_is_refused_with_the_lifecycles_message() -> None:
    # Setup
    store, _ = store_with_filed_item()
    with pytest.raises(LifecycleRefused) as refusal:
        a_lifecycle(store).keep("c1", True)

    # Execute
    reply = a_fix_handler(store).apply("stash:k:c1:1")

    # Assert
    assert reply == refused(str(refusal.value))


def test_keeping_an_item_that_is_no_longer_done_leaves_the_item_unchanged() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    a_fix_handler(store).apply("stash:k:c1:1")

    # Assert
    assert store.get_item("c1") == item


def test_pressing_keep_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:k:ghost:1")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("choice", INVALID_KEEP_CHOICES)
def test_an_invalid_keep_choice_answers_gone(choice: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:{choice}")

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("choice", INVALID_KEEP_CHOICES)
def test_an_invalid_keep_choice_changes_nothing(choice: str) -> None:
    # Setup
    store = a_store_with_a_completed_item()
    before = fetched_item(store, COMPLETED_ITEM_ID)

    # Execute
    a_fix_handler(store).apply(f"stash:k:{COMPLETED_ITEM_ID}:{choice}")

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID) == before
