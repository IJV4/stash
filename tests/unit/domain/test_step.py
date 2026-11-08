from datetime import datetime
from typing import Any

import pytest
from builders import UNSAFE_WIRE_IDS
from step_builders import a_step

from stash.domain import MAX_LEAD_DAYS, MIN_LEAD_DAYS, STEP_TEXT_LIMIT

A_DATETIME: Any = datetime(2026, 12, 1, 9, 0)


def test_a_lead_days_step_has_no_due_date_while_the_item_is_undated() -> None:
    # Setup
    step = a_step(lead_days=7, due_on=None)

    # Execute
    due = step.due_date(None)

    # Assert
    assert due is None


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_a_step_with_blank_text_is_refused(text: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="text must not be blank"):
        a_step(text=text)


def test_a_step_text_one_over_the_limit_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=f"at most {STEP_TEXT_LIMIT} characters"):
        a_step(text="x" * (STEP_TEXT_LIMIT + 1))


def test_the_step_text_limit_is_two_hundred_characters() -> None:
    # Assert
    assert STEP_TEXT_LIMIT == 200


def test_the_lead_days_range_is_zero_to_sixty() -> None:
    # Assert
    assert (MIN_LEAD_DAYS, MAX_LEAD_DAYS) == (0, 60)


@pytest.mark.parametrize("lead_days", [MIN_LEAD_DAYS - 1, MAX_LEAD_DAYS + 1])
def test_a_step_refuses_lead_days_outside_the_range(lead_days: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="lead_days must be between 0 and 60"):
        a_step(lead_days=lead_days)


def test_a_step_refuses_a_datetime_for_its_due_date() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="due_on must be a date, not a datetime"):
        a_step(lead_days=None, due_on=A_DATETIME)


def test_a_step_refuses_a_negative_position() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="position must not be negative"):
        a_step(position=-1)


@pytest.mark.parametrize("step_id", UNSAFE_WIRE_IDS)
def test_a_step_refuses_an_id_that_cannot_travel_in_callback_data(step_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="step id"):
        a_step(id=step_id)


@pytest.mark.parametrize("item_id", UNSAFE_WIRE_IDS)
def test_a_step_refuses_an_item_id_that_cannot_travel_in_callback_data(item_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="step item id"):
        a_step(item_id=item_id)
