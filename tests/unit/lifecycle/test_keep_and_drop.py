import pytest
from builders import NON_DONE_STAGES, an_item_at, fetched_item, stored
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
