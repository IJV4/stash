import logging

import pytest
from builders import NOT_PLANNED_STAGES, PLANNED_FOR, an_item_at, fetched_item, stored
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler, logged_by_applying
from fakes.memory_store import MemoryStore

from stash.capture import gone
from stash.capture.completion_replies import didnt_happen_reply
from stash.domain import Stage

NOT_HAPPENED = f"stash:h:i1:{PLANNED_FOR:%Y%m%d}"


def a_store_with_a_planned_item() -> MemoryStore:
    store = MemoryStore()
    stored(store, an_item_at(Stage.PLANNED, title="Date night"))
    return store


def test_pressing_didnt_happen_on_a_planned_item_answers_that_it_is_in_want_to() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    reply = a_fix_handler(store).apply(NOT_HAPPENED)

    # Assert
    assert reply == didnt_happen_reply(an_item_at(Stage.WANT_TO, title="Date night"))


def test_pressing_didnt_happen_on_a_planned_item_moves_it_to_want_to() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    a_fix_handler(store).apply(NOT_HAPPENED)

    # Assert
    assert fetched_item(store, "i1").stage is Stage.WANT_TO


def test_pressing_didnt_happen_on_a_planned_item_clears_its_date() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    a_fix_handler(store).apply(NOT_HAPPENED)

    # Assert
    assert fetched_item(store, "i1").date is None


def test_pressing_didnt_happen_twice_answers_the_same_in_want_to_text() -> None:
    # Setup
    store = a_store_with_a_planned_item()
    fixes = a_fix_handler(store)
    first = fixes.apply(NOT_HAPPENED)

    # Execute
    second = fixes.apply(NOT_HAPPENED)

    # Assert
    assert second == first


def test_pressing_didnt_happen_on_a_done_item_says_it_is_done_and_left_alone() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DONE, title="Date night"))

    # Execute
    reply = a_fix_handler(store).apply(NOT_HAPPENED)

    # Assert
    assert reply == didnt_happen_reply(an_item_at(Stage.DONE, title="Date night"))


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_pressing_didnt_happen_on_an_item_that_is_not_planned_leaves_it_unchanged(
    stage: Stage,
) -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(stage))

    # Execute
    a_fix_handler(store).apply(NOT_HAPPENED)

    # Assert
    assert fetched_item(store, "i1") == original


def test_pressing_didnt_happen_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:h:ghost:20261114")

    # Assert
    assert reply == gone()


def test_pressing_didnt_happen_for_an_unknown_item_is_logged_at_info() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute / Assert
    assert logged_by_applying(store, "stash:h:ghost:20261114") == [
        (logging.INFO, "fix callback for unknown item ghost")
    ]
