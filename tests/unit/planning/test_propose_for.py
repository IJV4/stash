import pytest
from builders import BASE
from capture_builders import sequential_ids
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, a_date_night, stored_date_night
from planning_rig import planning_over
from step_builders import a_step

from stash.domain import Stage
from stash.llm import LlmUnavailable
from stash.planning import PlanningRefused, ProposedStep, UnknownItem

TWO_PROPOSALS = (ProposedStep("Book the table", 14), ProposedStep("Pick an outfit", 2))


def test_proposing_returns_the_item_with_its_unconfirmed_steps_in_the_models_order() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    new_id = sequential_ids()
    first_id, second_id = new_id(), new_id()
    planning = planning_over(
        store, FakeStepProposals(TWO_PROPOSALS), lambda: BASE, sequential_ids()
    )

    # Execute
    proposal = planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert (proposal.item, proposal.steps) == (
        item,
        (
            a_step(id=first_id, item_id=DATE_NIGHT_ID, text="Book the table", lead_days=14),
            a_step(
                id=second_id, item_id=DATE_NIGHT_ID, text="Pick an outfit", lead_days=2, position=1
            ),
        ),
    )


def test_proposing_stores_the_steps_it_returns() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(TWO_PROPOSALS))

    # Execute
    proposal = planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == list(proposal.steps)


def test_proposing_asks_about_the_item_as_stored() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    proposals = FakeStepProposals(TWO_PROPOSALS)

    # Execute
    planning_over(store, proposals).propose_for(DATE_NIGHT_ID)

    # Assert
    assert proposals.asked_about == [item]


def test_proposing_stamps_every_step_with_the_current_instant() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(TWO_PROPOSALS), lambda: BASE)

    # Execute
    proposal = planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert {step.created_at for step in proposal.steps} == {BASE}


def test_a_model_with_nothing_to_propose_gives_an_empty_proposal_and_writes_no_steps() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(()))

    # Execute
    proposal = planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert (proposal.steps, store.step_writes) == ((), 0)


def test_proposing_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(FreshStore(), FakeStepProposals(TWO_PROPOSALS))

    # Execute / Assert
    with pytest.raises(UnknownItem) as refusal:
        planning.propose_for("nope")
    assert refusal.value.item_id == "nope"


def test_proposing_for_an_item_that_already_has_steps_is_refused_and_keeps_them() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    existing = a_step(item_id=DATE_NIGHT_ID, confirmed=True)
    store.save_steps(DATE_NIGHT_ID, [existing])
    planning = planning_over(store, FakeStepProposals(TWO_PROPOSALS))

    # Execute
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == [existing]


def test_proposing_for_an_item_that_is_not_planned_is_refused_without_asking_the_model() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store, stage=Stage.WANT_TO)
    proposals = FakeStepProposals(TWO_PROPOSALS)

    # Execute
    with pytest.raises(PlanningRefused):
        planning_over(store, proposals).propose_for(DATE_NIGHT_ID)

    # Assert
    assert proposals.asked_about == []


def test_a_model_that_is_unavailable_propagates_and_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(error=LlmUnavailable("down")))

    # Execute
    with pytest.raises(LlmUnavailable):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert (store.steps_for(DATE_NIGHT_ID), store.step_writes) == ([], 0)


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


def test_the_proposal_reflects_the_item_as_it_is_when_the_steps_are_written() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    retitled = a_date_night(title="Anniversary dinner")
    proposals = FakeStepProposals(TWO_PROPOSALS, while_thinking=lambda: store.save_item(retitled))

    # Execute
    proposal = planning_over(store, proposals).propose_for(DATE_NIGHT_ID)

    # Assert
    assert proposal.item == retitled
