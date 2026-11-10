from datetime import timedelta

import pytest
from builders import BASE, NAIVE

from stash.store import DuplicateOutcomeError, DuplicateStepError, UnknownItemError
from stash.store._checks import require_instant_range

ONE_MINUTE = timedelta(minutes=1)


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
