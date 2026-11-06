import pytest
from builders import (
    LATER,
    NOT_PLANNED_STAGES,
    PLANNED_FOR,
    an_item,
    an_item_at,
    fetched_item,
    stored,
)
from fakes.failing_save_store import FailingSaveStore
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import UnknownItem


def test_a_planned_item_that_did_not_happen_goes_back_to_want_to_with_no_date() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(stage=Stage.PLANNED, date=PLANNED_FOR))

    # Execute
    unplanned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1")

    # Assert
    assert (unplanned.stage, unplanned.date, unplanned.updated_at) == (Stage.WANT_TO, None, LATER)


def test_a_planned_item_that_did_not_happen_is_stored_back_in_want_to() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.PLANNED))

    # Execute
    unplanned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1")

    # Assert
    assert fetched_item(store, "i1") == unplanned


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_is_returned_unchanged(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(stage))

    # Execute
    returned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1")

    # Assert
    assert returned == original


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_is_not_written(stage: Stage) -> None:
    # Setup
    store = FailingSaveStore()
    stored(store, an_item_at(stage))
    store.fail_next_save = True

    # Execute
    returned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1")

    # Assert
    assert returned.stage is stage


def test_an_unknown_item_that_did_not_happen_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(MemoryStore()).didnt_happen("nope")

    # Assert
    assert raised.value.item_id == "nope"
