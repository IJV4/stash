import pytest
from builders import BASE
from fakes.fake_step_proposals import FakeStepProposals
from fakes.memory_store import MemoryStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, RESCHEDULED_ON, a_date_night, stored_date_night
from planning_rig import planning_over
from threads import run_in_thread

from stash.domain import Stage
from stash.planning import Planning, PlanningRefused, ProposedStep, UnknownItem

PROPOSALS = (ProposedStep("Book the table", 14),)
THINKING_LIMIT_SECONDS = 0.5


def agent_adds_a_step(planning: Planning) -> None:
    run_in_thread(
        lambda: planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10),
        THINKING_LIMIT_SECONDS,
    )


def test_a_step_the_agent_adds_while_the_model_is_thinking_is_never_overwritten() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night(store)
    proposals = FakeStepProposals(PROPOSALS, while_thinking=lambda: agent_adds_a_step(planning))
    planning = planning_over(store, proposals)

    # Execute
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert [step.text for step in store.steps_for(DATE_NIGHT_ID)] == ["Buy tickets"]


def test_an_item_moved_out_of_planned_while_the_model_is_thinking_gets_no_steps() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night(store)
    moved = a_date_night(stage=Stage.WANT_TO)
    proposals = FakeStepProposals(PROPOSALS, while_thinking=lambda: store.save_item(moved))

    # Execute
    with pytest.raises(PlanningRefused):
        planning_over(store, proposals).propose_for(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == []


def test_an_item_rescheduled_while_the_model_answers_with_no_steps_is_refused() -> None:
    # Setup
    store = MemoryStore()
    item = stored_date_night(store)
    proposals = FakeStepProposals(
        while_thinking=lambda: store.save_item(item.rescheduled(RESCHEDULED_ON, BASE))
    )

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning_over(store, proposals).propose_for(DATE_NIGHT_ID)


def test_an_item_rescheduled_while_the_model_answers_with_no_steps_is_not_declined() -> None:
    # Setup
    store = MemoryStore()
    item = stored_date_night(store)
    moved = item.rescheduled(RESCHEDULED_ON, BASE)
    proposals = FakeStepProposals(while_thinking=lambda: store.save_item(moved))
    planning = planning_over(store, proposals)
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Execute
    needed = planning.needs_proposal(moved)

    # Assert
    assert needed is True


def test_steps_proposed_for_an_item_rescheduled_while_the_model_was_thinking_are_not_saved() -> (
    None
):
    # Setup
    store = MemoryStore()
    item = stored_date_night(store)
    proposals = FakeStepProposals(
        PROPOSALS, while_thinking=lambda: store.save_item(item.rescheduled(RESCHEDULED_ON, BASE))
    )

    # Execute
    with pytest.raises(PlanningRefused):
        planning_over(store, proposals).propose_for(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == []


def test_an_item_deleted_while_the_model_is_thinking_is_unknown() -> None:
    # Setup
    store = MemoryStore()
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


def test_a_value_error_from_the_store_while_saving_proposed_steps_is_not_a_refusal() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    store.fail_step_writes_with(ValueError("the store broke"))

    # Execute / Assert
    with pytest.raises(ValueError, match="the store broke"):
        planning_over(store, FakeStepProposals(PROPOSALS)).propose_for(DATE_NIGHT_ID)
