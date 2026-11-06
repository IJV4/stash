from datetime import date, datetime
from typing import Any

import pytest
from builders import NAIVE, PLANNED_FOR, UNSAFE_WIRE_IDS
from step_builders import a_step

from stash.domain import MAX_LEAD_DAYS, MIN_LEAD_DAYS, STEP_TEXT_LIMIT

FIXED_DAY = date(2026, 12, 1)
A_DATETIME: Any = datetime(2026, 12, 1, 9, 0)


def test_a_step_built_with_a_due_date_has_no_lead_days() -> None:
    # Execute
    step = a_step(lead_days=None, due_on=FIXED_DAY)

    # Assert
    assert (step.lead_days, step.due_on) == (None, FIXED_DAY)


def test_a_lead_days_step_is_due_that_many_days_before_the_item_date() -> None:
    # Setup
    step = a_step(lead_days=7, due_on=None)

    # Execute
    due = step.due_date(PLANNED_FOR)

    # Assert
    assert due == date(2026, 11, 7)


def test_a_lead_days_step_has_no_due_date_while_the_item_is_undated() -> None:
    # Setup
    step = a_step(lead_days=7, due_on=None)

    # Execute
    due = step.due_date(None)

    # Assert
    assert due is None


def test_a_fixed_date_step_is_due_on_its_date_whatever_the_item_date() -> None:
    # Setup
    step = a_step(lead_days=None, due_on=FIXED_DAY)

    # Execute
    due = step.due_date(PLANNED_FOR)

    # Assert
    assert due == FIXED_DAY


def test_a_fixed_date_step_is_due_on_its_date_while_the_item_is_undated() -> None:
    # Setup
    step = a_step(lead_days=None, due_on=FIXED_DAY)

    # Execute
    due = step.due_date(None)

    # Assert
    assert due == FIXED_DAY


def test_a_zero_lead_days_step_is_due_on_the_item_date() -> None:
    # Execute
    due = a_step(lead_days=0).due_date(PLANNED_FOR)

    # Assert
    assert due == PLANNED_FOR


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_a_step_with_blank_text_is_refused(text: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="text must not be blank"):
        a_step(text=text)


def test_a_step_text_of_the_limit_length_is_accepted() -> None:
    # Execute
    step = a_step(text="x" * STEP_TEXT_LIMIT)

    # Assert
    assert len(step.text) == STEP_TEXT_LIMIT


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


@pytest.mark.parametrize("lead_days", [MIN_LEAD_DAYS, MAX_LEAD_DAYS])
def test_a_step_accepts_lead_days_at_either_end_of_the_range(lead_days: int) -> None:
    # Execute
    step = a_step(lead_days=lead_days)

    # Assert
    assert step.lead_days == lead_days


@pytest.mark.parametrize("lead_days", [MIN_LEAD_DAYS - 1, MAX_LEAD_DAYS + 1])
def test_a_step_refuses_lead_days_outside_the_range(lead_days: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="lead_days must be between 0 and 60"):
        a_step(lead_days=lead_days)


def test_a_step_with_both_lead_days_and_a_due_date_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="exactly one of lead_days and due_on"):
        a_step(lead_days=7, due_on=FIXED_DAY)


def test_a_step_with_neither_lead_days_nor_a_due_date_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="exactly one of lead_days and due_on"):
        a_step(lead_days=None, due_on=None)


def test_a_step_refuses_a_datetime_for_its_due_date() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="due_on must be a date, not a datetime"):
        a_step(lead_days=None, due_on=A_DATETIME)


def test_a_step_accepts_position_zero() -> None:
    # Execute
    step = a_step(position=0)

    # Assert
    assert step.position == 0


def test_a_step_refuses_a_negative_position() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="position must not be negative"):
        a_step(position=-1)


def test_a_step_refuses_a_naive_created_at() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        a_step(created_at=NAIVE)


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


def test_confirming_a_step_returns_a_confirmed_step() -> None:
    # Execute
    confirmed = a_step(confirmed=False).confirmed_now()

    # Assert
    assert confirmed.confirmed is True


def test_confirming_a_step_changes_nothing_else() -> None:
    # Setup
    step = a_step()

    # Execute
    confirmed = step.confirmed_now()

    # Assert
    assert confirmed == a_step(confirmed=True)


def test_confirming_a_step_leaves_the_original_unconfirmed() -> None:
    # Setup
    step = a_step(confirmed=False)

    # Execute
    step.confirmed_now()

    # Assert
    assert step.confirmed is False


def test_confirming_an_already_confirmed_step_changes_nothing() -> None:
    # Setup
    step = a_step(confirmed=True)

    # Execute
    again = step.confirmed_now()

    # Assert
    assert again == step


def test_marking_a_step_done_returns_a_done_step() -> None:
    # Execute
    finished = a_step(done=False).marked_done()

    # Assert
    assert finished.done is True


def test_marking_a_step_done_changes_nothing_else() -> None:
    # Execute
    finished = a_step().marked_done()

    # Assert
    assert finished == a_step(done=True)


def test_marking_a_step_done_leaves_the_original_open() -> None:
    # Setup
    step = a_step(done=False)

    # Execute
    step.marked_done()

    # Assert
    assert step.done is False


def test_marking_an_already_done_step_done_changes_nothing() -> None:
    # Setup
    step = a_step(done=True)

    # Execute
    again = step.marked_done()

    # Assert
    assert again == step


def test_an_unconfirmed_step_can_be_marked_done() -> None:
    # Execute
    finished = a_step(confirmed=False).marked_done()

    # Assert
    assert (finished.confirmed, finished.done) == (False, True)
