from datetime import date
from typing import Any

import pytest

from stash.hermes_adapter.tool_arguments import ToolArguments


def arguments(**values: Any) -> ToolArguments:
    return ToolArguments.of(values)


@pytest.mark.parametrize("values", [{}, {"lead_days": None}])
def test_an_absent_lead_time_is_none(values: dict[str, Any]) -> None:
    # Execute
    lead_days = ToolArguments.of(values).optional_lead_days()

    # Assert
    assert lead_days is None


def test_a_lead_time_of_zero_is_kept_not_read_as_absent() -> None:
    # Execute
    lead_days = arguments(lead_days=0).optional_lead_days()

    # Assert
    assert lead_days == 0


@pytest.mark.parametrize("raw", [True, False, "7", 7.0, [7]])
def test_a_lead_time_that_is_not_an_integer_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="lead_days must be an integer"):
        arguments(lead_days=raw).optional_lead_days()


@pytest.mark.parametrize("values", [{}, {"due_on": None}])
def test_an_absent_due_date_is_none(values: dict[str, Any]) -> None:
    # Execute
    due_on = ToolArguments.of(values).optional_due_on()

    # Assert
    assert due_on is None


def test_a_due_date_is_read_from_its_iso_text() -> None:
    # Execute
    due_on = arguments(due_on="2027-02-12").optional_due_on()

    # Assert
    assert due_on == date(2027, 2, 12)


@pytest.mark.parametrize("raw", ["12/02/2027", "2027-2-12", "20270212", "2027-02-30", 5, True])
def test_a_due_date_that_is_not_an_iso_date_is_refused_naming_the_field(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="due_on must be"):
        arguments(due_on=raw).optional_due_on()
