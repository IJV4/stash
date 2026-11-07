import pytest
from fakes.busy_store import BusyStore
from fakes.fake_step_proposals import FakeStepProposals
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_builders import a_step

from stash.planning import PlanningBusy


def test_planning_reports_a_busy_store_as_planning_busy() -> None:
    # Setup
    store = BusyStore()
    stored_date_night(store)
    store.save_step(a_step(item_id=DATE_NIGHT_ID))
    planning = planning_over(store, FakeStepProposals())

    # Execute / Assert
    with pytest.raises(PlanningBusy):
        planning.confirm_all(DATE_NIGHT_ID)
