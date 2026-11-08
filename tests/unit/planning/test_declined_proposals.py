import pytest
from builders import BASE, stored
from fakes.chat_model import FakeChatModel
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import (
    DATE_NIGHT_ID,
    RESCHEDULED_ON,
    a_date_night,
    a_raw_step,
    stored_date_night,
)
from planning_rig import a_planning, planning_over
from step_edit_rig import confirmed, date_night_with, proposed

from stash.llm import LlmBadOutput, LlmDeferred, LlmError, LlmUnavailable
from stash.planning import PlanningRefused
from stash.planning.declines import Declines


def test_after_discarding_a_proposal_the_item_no_longer_needs_one() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = planning_over(store, FakeStepProposals())

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_after_the_model_answers_with_no_steps_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = a_planning(store, FakeChatModel({"steps": []}))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_after_an_answer_whose_every_step_is_unusable_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    unusable = {"steps": [a_raw_step(lead_days=True), a_raw_step(lead_days=False)]}
    planning = a_planning(store, FakeChatModel(unusable))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


def test_after_unusable_model_output_the_item_no_longer_needs_a_proposal() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(error=LlmBadOutput("not json")))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(item) is False


@pytest.mark.parametrize("outage", [LlmUnavailable("down"), LlmDeferred("busy")])
def test_after_an_outage_the_item_still_needs_a_proposal(outage: LlmError) -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(error=outage))

    # Execute
    with pytest.raises(LlmError):
        planning.propose_for(DATE_NIGHT_ID)
    needed = planning.needs_proposal(item)

    # Assert
    assert needed is True


def test_a_declined_item_is_offered_again_once_its_date_changes() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    planning = planning_over(store, FakeStepProposals())
    planning.discard(DATE_NIGHT_ID)
    moved = item.rescheduled(RESCHEDULED_ON, BASE)
    store.save_item(moved)

    # Execute
    needed = planning.needs_proposal(moved)

    # Assert
    assert needed is True


def test_proposing_for_a_declined_item_is_refused_without_asking_the_model() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals()
    planning = planning_over(store, proposals)
    planning.discard(DATE_NIGHT_ID)

    # Execute
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert proposals.asked_about == []


def test_discarding_one_item_does_not_decline_another_item() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    other = stored(store, a_date_night(id="museum"))
    planning = planning_over(store, FakeStepProposals())

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(other) is True


def test_discarding_records_the_decline_even_when_only_confirmed_steps_exist() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, [confirmed("s1", 0)])
    planning = planning_over(store, FakeStepProposals())

    # Execute
    planning.discard(DATE_NIGHT_ID)
    store.save_steps(DATE_NIGHT_ID, [])
    needed = planning.needs_proposal(item)

    # Assert
    assert needed is False


def test_when_removing_the_proposed_steps_fails_the_decline_is_already_recorded() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store, proposed("s1", 0))
    store.fail_step_writes_with(RuntimeError("disk full"))

    # Execute
    with pytest.raises(RuntimeError):
        planning.discard(DATE_NIGHT_ID)

    # Assert
    assert Declines(store).is_declined(a_date_night()) is True


def test_when_removing_the_proposed_steps_fails_they_are_still_there() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store, proposed("s1", 0))
    store.fail_step_writes_with(RuntimeError("disk full"))

    # Execute
    with pytest.raises(RuntimeError):
        planning.discard(DATE_NIGHT_ID)

    # Assert
    assert [step.id for step in store.steps_for(DATE_NIGHT_ID)] == ["s1"]
