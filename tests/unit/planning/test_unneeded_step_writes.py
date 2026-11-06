from fakes.fake_step_proposals import FakeStepProposals
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_edit_rig import confirmed, date_night_with


def test_confirming_steps_that_are_all_confirmed_already_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store, confirmed("s1", 0), confirmed("s2", 1))
    writes_before = store.step_writes

    # Execute
    planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert store.step_writes == writes_before


def test_discarding_when_every_step_is_confirmed_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store, confirmed("s1", 0), confirmed("s2", 1))
    writes_before = store.step_writes

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert store.step_writes == writes_before


def test_discarding_an_item_without_steps_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals())

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert store.step_writes == 0
