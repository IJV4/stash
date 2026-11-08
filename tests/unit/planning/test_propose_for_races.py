import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over

from stash.planning import ProposedStep, UnknownItem

PROPOSALS = (ProposedStep("Book the table", 14),)


def test_an_item_deleted_while_the_model_is_thinking_is_unknown() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals(
        PROPOSALS, while_thinking=lambda: store.delete_item(DATE_NIGHT_ID)
    )

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning_over(store, proposals).propose_for(DATE_NIGHT_ID)


def test_an_item_deleted_just_before_the_steps_are_written_is_unknown() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    store.vanish_before_next_step_write(DATE_NIGHT_ID)

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning_over(store, FakeStepProposals(PROPOSALS)).propose_for(DATE_NIGHT_ID)
