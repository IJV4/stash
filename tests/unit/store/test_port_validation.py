from datetime import timedelta

import pytest
from builders import BASE, COMPLETED_ON, NAIVE, an_item, an_outcome, days_after
from step_builders import a_step

from stash.store import DuplicateOutcomeError, DuplicateStepError, UnknownItemError
from stash.store.port import (
    require_date_range,
    require_instant_range,
    require_outcome_for_item,
    require_steps_for_item,
)

ONE_MINUTE = timedelta(minutes=1)


def test_a_date_range_that_starts_after_it_ends_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="start must not be after end"):
        require_date_range(days_after(1), COMPLETED_ON)


def test_a_date_range_of_a_single_day_is_accepted() -> None:
    # Execute / Assert
    require_date_range(COMPLETED_ON, COMPLETED_ON)


def test_a_date_range_that_ends_after_it_starts_is_accepted() -> None:
    # Execute / Assert
    require_date_range(COMPLETED_ON, days_after(1))


def test_an_outcome_of_another_item_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="i2"):
        require_outcome_for_item(an_item(), an_outcome(item_id="i2"))


def test_an_outcome_of_the_same_item_is_accepted() -> None:
    # Execute / Assert
    require_outcome_for_item(an_item(), an_outcome())


def test_a_duplicate_outcome_error_names_the_outcome_id() -> None:
    # Execute
    error = DuplicateOutcomeError("o7")

    # Assert
    assert "o7" in str(error)


def test_a_duplicate_outcome_error_is_a_value_error() -> None:
    # Execute
    error = DuplicateOutcomeError("o7")

    # Assert
    assert isinstance(error, ValueError)


def test_an_unknown_item_error_carries_the_item_id() -> None:
    # Execute
    error = UnknownItemError("i7")

    # Assert
    assert error.item_id == "i7"


def test_an_unknown_item_error_still_reads_as_the_item_id() -> None:
    # Execute
    error = UnknownItemError("i7")

    # Assert
    assert str(error) == "i7"


def test_a_step_of_another_item_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="i2"):
        require_steps_for_item("i1", [a_step(item_id="i2")])


def test_a_repeated_step_id_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="s1"):
        require_steps_for_item("i1", [a_step(), a_step(position=1)])


def test_distinct_steps_of_the_same_item_are_accepted() -> None:
    # Execute / Assert
    require_steps_for_item("i1", [a_step(), a_step(id="s2", position=1)])


def test_no_steps_are_accepted() -> None:
    # Execute / Assert
    require_steps_for_item("i1", [])


def test_an_instant_range_with_a_naive_start_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="start must be timezone-aware"):
        require_instant_range(NAIVE, BASE)


def test_an_instant_range_with_a_naive_end_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="end must be timezone-aware"):
        require_instant_range(BASE, NAIVE)


def test_an_instant_range_that_starts_after_it_ends_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="start must not be after end"):
        require_instant_range(BASE + ONE_MINUTE, BASE)


def test_an_instant_range_of_a_single_instant_is_accepted() -> None:
    # Execute / Assert
    require_instant_range(BASE, BASE)


def test_an_instant_range_that_ends_after_it_starts_is_accepted() -> None:
    # Execute / Assert
    require_instant_range(BASE, BASE + ONE_MINUTE)


def test_a_naive_start_against_an_aware_end_is_refused_before_the_bounds_are_compared() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="start must be timezone-aware"):
        require_instant_range(NAIVE, BASE.replace(year=2000))


def test_a_naive_end_against_an_aware_start_is_refused_before_the_bounds_are_compared() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="end must be timezone-aware"):
        require_instant_range(BASE, NAIVE.replace(year=2000))


def test_a_duplicate_step_error_names_the_step_id() -> None:
    # Execute
    error = DuplicateStepError("s7")

    # Assert
    assert "s7" in str(error)


def test_a_duplicate_step_error_is_a_value_error() -> None:
    # Execute
    error = DuplicateStepError("s7")

    # Assert
    assert isinstance(error, ValueError)
