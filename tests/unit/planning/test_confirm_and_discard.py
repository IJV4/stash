import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.faulty_store import FaultyStore, step_writes
from fakes.store_factories import FreshStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_edit_rig import date_night_with, proposed

from stash.planning import UnknownItem
from stash.store import UnknownItemError


def test_confirming_twice_returns_the_same_steps() -> None:
    # Setup
    planning = date_night_with(FreshStore(), proposed("s1", 0))
    first = planning.confirm_all(DATE_NIGHT_ID)

    # Execute
    second = planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert second == first


def test_confirming_an_item_without_steps_returns_nothing_and_writes_nothing() -> None:
    # Setup
    store = FaultyStore(record=True)
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals())

    # Execute
    steps = planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert (steps, step_writes(store)) == ((), 0)


def test_confirming_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(FreshStore(), FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.confirm_all("nope")


def test_confirming_for_an_item_deleted_just_before_the_write_is_unknown() -> None:
    # Setup
    store = FaultyStore(record=True)
    stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, [proposed("s1", 0)])
    store.fail_next("save_steps", UnknownItemError(DATE_NIGHT_ID))
    planning = planning_over(store, FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.confirm_all(DATE_NIGHT_ID)


def test_discarding_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(FreshStore(), FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.discard("nope")


def test_discarding_for_an_item_deleted_just_before_the_write_is_unknown() -> None:
    # Setup
    store = FaultyStore(record=True)
    stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, [proposed("s1", 0)])
    store.fail_next("save_steps", UnknownItemError(DATE_NIGHT_ID))
    planning = planning_over(store, FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.discard(DATE_NIGHT_ID)
