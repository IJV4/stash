from datetime import timedelta

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
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import ItemChanged, UnknownItem


def test_a_planned_item_that_did_not_happen_goes_back_to_want_to_with_no_date() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item(stage=Stage.PLANNED, date=PLANNED_FOR))

    # Execute
    unplanned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1", PLANNED_FOR)

    # Assert
    assert (unplanned.stage, unplanned.date, unplanned.updated_at) == (Stage.WANT_TO, None, LATER)


def test_a_planned_item_that_did_not_happen_is_stored_back_in_want_to() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.PLANNED))

    # Execute
    unplanned = a_lifecycle(store, clock=lambda: LATER).didnt_happen("i1", PLANNED_FOR)

    # Assert
    assert fetched_item(store, "i1") == unplanned


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
    store = FailingSaveStore()
    stored(store, an_item_at(stage))
    store.fail_next_save = True

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


def test_a_planned_item_asked_about_for_another_date_raises_item_changed() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.PLANNED))

    # Execute / Assert
    with pytest.raises(ItemChanged):
        a_lifecycle(store).didnt_happen("i1", PLANNED_FOR + timedelta(days=7))


def test_a_planned_item_asked_about_for_another_date_stays_as_it_was() -> None:
    # Setup
    store = FreshStore()
    planned = stored(store, an_item_at(Stage.PLANNED))

    # Execute
    with pytest.raises(ItemChanged):
        a_lifecycle(store).didnt_happen("i1", PLANNED_FOR + timedelta(days=7))

    # Assert
    assert fetched_item(store, "i1") == planned
