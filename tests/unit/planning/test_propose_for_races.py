from collections.abc import Callable

import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.faulty_store import FaultyStore
from fakes.store_factories import FreshStore
from planning_builders import DATE_NIGHT_ID, RESCHEDULED_ON, a_date_night, stored_date_night
from planning_rig import planning_over

from stash.domain import Item, Stage
from stash.llm import LlmBadOutput
from stash.planning import Planning, PlanningRefused, ProposalUnusable, ProposedStep, UnknownItem
from stash.store import Store, UnknownItemError

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
    store = FaultyStore(record=True)
    stored_date_night(store)
    store.fail_next("save_steps", UnknownItemError(DATE_NIGHT_ID))

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning_over(store, FakeStepProposals(PROPOSALS)).propose_for(DATE_NIGHT_ID)


@pytest.mark.parametrize(
    "changed",
    [a_date_night(date=RESCHEDULED_ON), a_date_night(stage=Stage.DOING)],
    ids=["rescheduled", "no-longer-planned"],
)
def test_an_unusable_answer_does_not_decline_an_item_changed_while_the_model_thought(
    changed: Item,
) -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals(
        error=LlmBadOutput("not json"), while_thinking=lambda: store.save_item(changed)
    )
    planning = planning_over(store, proposals)

    # Execute
    with pytest.raises(ProposalUnusable):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert planning.needs_proposal(a_date_night(date=changed.date)) is True


@pytest.mark.parametrize(
    ("change", "step_texts"),
    [
        (
            lambda _, planning: planning.add_step(DATE_NIGHT_ID, "Buy flowers", lead_days=7),
            ["Buy flowers"],
        ),
        (lambda store, _: store.save_item(a_date_night(date=RESCHEDULED_ON)), []),
        (lambda store, _: store.save_item(a_date_night(stage=Stage.DOING)), []),
    ],
    ids=["owner-added-step", "rescheduled", "no-longer-planned"],
)
def test_a_proposal_is_refused_and_steps_are_left_alone_if_the_item_changed_while_the_model_thought(
    change: Callable[[Store, Planning], object], step_texts: list[str]
) -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals(PROPOSALS, while_thinking=lambda: change(store, planning))
    planning = planning_over(store, proposals)

    # Execute
    with pytest.raises(PlanningRefused):
        planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert [step.text for step in store.steps_for(DATE_NIGHT_ID)] == step_texts
