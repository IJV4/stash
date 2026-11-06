import pytest
from planning_builders import a_raw_step

from stash.domain import MAX_LEAD_DAYS, MIN_LEAD_DAYS
from stash.planning import parse_steps

NOT_WHOLE_NUMBERS = [True, False, 3.5, 3.0, "-3 days", "in 400 days", "7", None, [7], {"days": 7}]


def lead_days_of(value: object) -> list[int]:
    return [step.lead_days for step in parse_steps({"steps": [a_raw_step(lead_days=value)]})]


@pytest.mark.parametrize("value", NOT_WHOLE_NUMBERS, ids=repr)
def test_an_entry_whose_lead_days_is_not_a_whole_number_is_skipped(value: object) -> None:
    # Execute
    lead_days = lead_days_of(value)

    # Assert
    assert lead_days == []


def test_an_entry_without_lead_days_is_skipped() -> None:
    # Execute
    steps = parse_steps({"steps": [{"text": "Book the table"}]})

    # Assert
    assert steps == ()


def test_lead_days_within_the_range_are_kept() -> None:
    # Execute
    lead_days = lead_days_of(5)

    # Assert
    assert lead_days == [5]


def test_zero_lead_days_means_the_same_day_and_is_kept() -> None:
    # Execute
    lead_days = lead_days_of(MIN_LEAD_DAYS)

    # Assert
    assert lead_days == [0]


def test_the_maximum_lead_days_is_kept() -> None:
    # Execute
    lead_days = lead_days_of(MAX_LEAD_DAYS)

    # Assert
    assert lead_days == [MAX_LEAD_DAYS]


def test_negative_lead_days_are_clamped_to_the_same_day() -> None:
    # Execute
    lead_days = lead_days_of(-3)

    # Assert
    assert lead_days == [MIN_LEAD_DAYS]


def test_lead_days_above_the_maximum_are_clamped_to_it() -> None:
    # Execute
    lead_days = lead_days_of(400)

    # Assert
    assert lead_days == [MAX_LEAD_DAYS]


def test_one_more_than_the_maximum_is_clamped_to_it() -> None:
    # Execute
    lead_days = lead_days_of(MAX_LEAD_DAYS + 1)

    # Assert
    assert lead_days == [MAX_LEAD_DAYS]
