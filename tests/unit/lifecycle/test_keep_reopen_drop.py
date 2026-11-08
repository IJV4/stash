import pytest
from builders import LATER, NON_DONE_STAGES, an_item_at, fetched_item, stored, stored_completion
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import LifecycleRefused, UnknownItem

BLANK_REASONS = ["", "   ", None]


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_keeping_an_item_that_is_not_done_is_refused_and_changes_nothing(stage: Stage) -> None:
    # Setup
    store = FreshStore()
    original = stored(store, an_item_at(stage))

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).keep("i1", True)

    # Assert
    assert fetched_item(store, "i1") == original


def test_keeping_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(FreshStore()).keep("nope", True)

    # Assert
    assert raised.value.item_id == "nope"


def test_reopening_a_done_item_puts_it_back_to_want_to_still_kept_and_stores_it() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "i1", kept=True)

    # Execute
    reopened = a_lifecycle(store, clock=lambda: LATER).reopen("i1")

    # Assert
    assert (reopened.stage, reopened.kept, fetched_item(store, "i1")) == (
        Stage.WANT_TO,
        True,
        reopened,
    )


def test_reopening_a_done_item_keeps_its_outcomes() -> None:
    # Setup
    store = FreshStore()
    stored_completion(store, "i1")
    outcomes = store.outcomes_for("i1")

    # Execute
    a_lifecycle(store).reopen("i1")

    # Assert
    assert store.outcomes_for("i1") == outcomes


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_reopening_an_item_that_is_not_done_is_refused_and_changes_nothing(stage: Stage) -> None:
    # Setup
    store = FreshStore()
    original = stored(store, an_item_at(stage))

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).reopen("i1")

    # Assert
    assert fetched_item(store, "i1") == original


def test_reopening_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(FreshStore()).reopen("nope")

    # Assert
    assert raised.value.item_id == "nope"


def test_dropping_with_a_reason_over_300_characters_is_refused_and_changes_nothing() -> None:
    # Setup
    store = FreshStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).drop("i1", "r" * 301)

    # Assert
    assert fetched_item(store, "i1") == original


def test_dropping_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(FreshStore()).drop("nope", "why")

    # Assert
    assert raised.value.item_id == "nope"
