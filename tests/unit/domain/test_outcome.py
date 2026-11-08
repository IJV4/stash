from typing import Any

import pytest
from builders import BASE, LATER, NAIVE, UNSAFE_WIRE_IDS, an_outcome

from stash.domain.outcome import (
    MAX_TAKEAWAYS,
    OUTCOME_NOTES_LIMIT,
    TAKEAWAY_LIMIT,
)

OUT_OF_RANGE_RATINGS = [0, 6, -1]


@pytest.mark.parametrize("rating", OUT_OF_RANGE_RATINGS)
def test_an_outcome_refuses_a_rating_outside_one_to_five(rating: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="rating"):
        an_outcome(rating=rating)


def test_an_outcome_refuses_notes_over_the_maximum_length() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be at most 4000 characters"):
        an_outcome(notes="n" * (OUTCOME_NOTES_LIMIT + 1))


def test_an_outcome_refuses_more_than_the_maximum_number_of_takeaways() -> None:
    # Setup
    takeaways = tuple(f"take {number}" for number in range(MAX_TAKEAWAYS + 1))

    # Execute / Assert
    with pytest.raises(ValueError, match="takeaways must have at most 20 entries"):
        an_outcome(takeaways=takeaways)


def test_an_outcome_refuses_a_takeaway_over_the_maximum_length() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="takeaway must be at most 500 characters"):
        an_outcome(takeaways=("t" * (TAKEAWAY_LIMIT + 1),))


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_an_outcome_refuses_a_blank_takeaway(blank: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="takeaway must not be blank"):
        an_outcome(takeaways=("Salt early", blank))


def test_an_outcome_given_a_bare_string_for_takeaways_raises_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="takeaways must be a collection of strings"):
        an_outcome(takeaways="Salt early")


@pytest.mark.parametrize("outcome_id", UNSAFE_WIRE_IDS)
def test_an_outcome_refuses_an_id_that_cannot_travel_in_callback_data(outcome_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="outcome id"):
        an_outcome(id=outcome_id)


@pytest.mark.parametrize("item_id", UNSAFE_WIRE_IDS)
def test_an_outcome_refuses_an_item_id_that_cannot_travel_in_callback_data(item_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="outcome item id"):
        an_outcome(item_id=item_id)


def test_an_outcome_completed_on_a_datetime_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="completed_on must be a date, not a datetime"):
        an_outcome(completed_on=BASE)


def test_an_outcome_with_naive_recorded_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="recorded_at"):
        an_outcome(recorded_at=NAIVE)


def test_with_notes_over_the_notes_limit_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be at most 4000 characters"):
        outcome.with_notes("n" * (OUTCOME_NOTES_LIMIT + 1), (), LATER)


def test_with_notes_with_too_many_takeaways_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()
    takeaways = tuple(f"take {number}" for number in range(MAX_TAKEAWAYS + 1))

    # Execute / Assert
    with pytest.raises(ValueError, match="takeaways must have at most 20 entries"):
        outcome.with_notes("Better", takeaways, LATER)


def test_with_notes_with_a_blank_takeaway_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="takeaway must not be blank"):
        outcome.with_notes("Better", (" ",), LATER)


def test_with_notes_with_an_overlong_takeaway_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="takeaway must be at most 500 characters"):
        outcome.with_notes("Better", ("t" * (TAKEAWAY_LIMIT + 1),), LATER)


def test_with_notes_given_a_bare_string_for_takeaways_raises_type_error() -> None:
    # Setup
    outcome = an_outcome()
    bare_string: Any = "Less salt"

    # Execute / Assert
    with pytest.raises(TypeError, match="takeaways must be a collection of strings"):
        outcome.with_notes("Better", bare_string, LATER)


def test_with_notes_with_naive_now_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="edited_at"):
        outcome.with_notes("Better", (), NAIVE)


def test_an_outcome_with_naive_edited_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="edited_at"):
        an_outcome(edited_at=NAIVE)
