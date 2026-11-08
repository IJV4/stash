import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over

from stash.planning import PlanningRefused, ProposedStep, UnknownItem

TWO_PROPOSALS = (ProposedStep("Book the table", 14), ProposedStep("Pick an outfit", 2))


def test_proposing_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(FreshStore(), FakeStepProposals(TWO_PROPOSALS))

    # Execute / Assert
    with pytest.raises(UnknownItem) as refusal:
        planning.propose_for("nope")
    assert refusal.value.item_id == "nope"


def test_a_proposed_step_the_domain_refuses_is_a_planning_refusal_and_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals((ProposedStep("", 3),)))

    # Execute
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert store.step_writes == 0
