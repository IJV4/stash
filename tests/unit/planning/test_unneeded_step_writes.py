from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID
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
