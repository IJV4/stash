from fakes.faulty_store import FaultyStore, step_writes
from planning_builders import DATE_NIGHT_ID
from step_edit_rig import confirmed, date_night_with


def test_confirming_steps_that_are_all_confirmed_already_writes_nothing() -> None:
    # Setup
    store = FaultyStore(record=True)
    planning = date_night_with(store, confirmed("s1", 0), confirmed("s2", 1))
    writes_before = step_writes(store)

    # Execute
    planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert step_writes(store) == writes_before
