import pytest
from builders import COMPLETED_ON, an_item, an_outcome, days_after

from stash.store import DuplicateOutcomeError, UnknownItemError
from stash.store.port import require_date_range, require_outcome_for_item


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
