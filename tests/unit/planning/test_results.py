import pytest
from builders import BASE, an_item
from step_builders import a_step

from stash.planning.results import Proposal, ProposedStep


def test_a_proposed_step_becomes_an_unconfirmed_step_with_the_given_identity_and_position() -> None:
    # Setup
    proposed = ProposedStep("Book the table", 7)

    # Execute
    step = proposed.as_step("s1", "i1", 2, BASE)

    # Assert
    assert step == a_step(
        id="s1",
        item_id="i1",
        text="Book the table",
        lead_days=7,
        due_on=None,
        confirmed=False,
        done=False,
        position=2,
        created_at=BASE,
    )


def test_a_proposed_step_with_blank_text_is_refused_when_it_becomes_a_step() -> None:
    # Setup
    proposed = ProposedStep("", 7)

    # Execute / Assert
    with pytest.raises(ValueError, match="text"):
        proposed.as_step("s1", "i1", 0, BASE)


def test_a_proposed_step_with_lead_days_out_of_range_is_refused_when_it_becomes_a_step() -> None:
    # Setup
    proposed = ProposedStep("Book the table", 61)

    # Execute / Assert
    with pytest.raises(ValueError, match="lead_days"):
        proposed.as_step("s1", "i1", 0, BASE)


def test_a_proposal_carries_the_item_and_its_steps() -> None:
    # Setup
    item = an_item()
    steps = (a_step(),)

    # Execute
    proposal = Proposal(item, steps)

    # Assert
    assert (proposal.item, proposal.steps) == (item, steps)
