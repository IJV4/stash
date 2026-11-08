import pytest
from builders import (
    LATER,
    NOT_PLANNED_STAGES,
    PLANNED_FOR,
    an_item_at,
    stored,
)
from fakes.faulty_store import FaultyStore, StoreFault
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import UnknownItem


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_is_returned_unchanged(stage: Stage) -> None:
    # Setup
    store = FreshStore()
    original = stored(store, an_item_at(stage))

    # Execute
    returned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1", PLANNED_FOR)

    # Assert
    assert returned == original


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_is_not_written(stage: Stage) -> None:
    # Setup
    store = FaultyStore()
    stored(store, an_item_at(stage))
    store.fail_next("update_item", StoreFault("save"))

    # Execute
    returned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1", PLANNED_FOR)

    # Assert
    assert returned.stage is stage


def test_an_unknown_item_that_did_not_happen_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(FreshStore()).didnt_happen("nope", PLANNED_FOR)

    # Assert
    assert raised.value.item_id == "nope"
