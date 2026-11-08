import pytest
from builders import BASE

from stash.planning.results import ProposedStep


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
