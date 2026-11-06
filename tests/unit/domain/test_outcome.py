from typing import Any

import pytest
from builders import BASE, COMPLETED_ON, LATER, NAIVE, UNSAFE_WIRE_IDS, an_outcome

from stash.domain.outcome import (
    MAX_TAKEAWAYS,
    OUTCOME_NOTES_LIMIT,
    TAKEAWAY_LIMIT,
)

OUT_OF_RANGE_RATINGS = [0, 6, -1]


def test_an_outcome_keeps_the_values_it_was_built_with() -> None:
    # Setup / Execute
    outcome = an_outcome()

    # Assert
    assert (
        outcome.id,
        outcome.item_id,
        outcome.completed_on,
        outcome.rating,
        outcome.notes,
        outcome.takeaways,
        outcome.recorded_at,
        outcome.edited_at,
    ) == ("o1", "i1", COMPLETED_ON, 4, "Great", ("Salt early",), BASE, None)


def test_an_outcome_without_a_rating_is_accepted() -> None:
    # Execute
    outcome = an_outcome(rating=None)

    # Assert
    assert outcome.rating is None


@pytest.mark.parametrize("rating", range(1, 6))
def test_an_outcome_accepts_every_rating_from_one_to_five(rating: int) -> None:
    # Execute
    outcome = an_outcome(rating=rating)

    # Assert
    assert outcome.rating == rating


@pytest.mark.parametrize("rating", OUT_OF_RANGE_RATINGS)
def test_an_outcome_refuses_a_rating_outside_one_to_five(rating: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="rating"):
        an_outcome(rating=rating)


def test_an_outcome_accepts_blank_notes() -> None:
    # Execute
    outcome = an_outcome(notes="")

    # Assert
    assert outcome.notes == ""


def test_an_outcome_accepts_notes_of_the_maximum_length() -> None:
    # Execute
    outcome = an_outcome(notes="n" * OUTCOME_NOTES_LIMIT)

    # Assert
    assert len(outcome.notes) == OUTCOME_NOTES_LIMIT


def test_an_outcome_refuses_notes_over_the_maximum_length() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be at most 4000 characters"):
        an_outcome(notes="n" * (OUTCOME_NOTES_LIMIT + 1))


def test_an_outcome_accepts_the_maximum_number_of_takeaways() -> None:
    # Setup
    takeaways = tuple(f"take {number}" for number in range(MAX_TAKEAWAYS))

    # Execute
    outcome = an_outcome(takeaways=takeaways)

    # Assert
    assert outcome.takeaways == takeaways


def test_an_outcome_refuses_more_than_the_maximum_number_of_takeaways() -> None:
    # Setup
    takeaways = tuple(f"take {number}" for number in range(MAX_TAKEAWAYS + 1))

    # Execute / Assert
    with pytest.raises(ValueError, match="takeaways must have at most 20 entries"):
        an_outcome(takeaways=takeaways)


def test_an_outcome_accepts_a_takeaway_of_the_maximum_length() -> None:
    # Execute
    outcome = an_outcome(takeaways=("t" * TAKEAWAY_LIMIT,))

    # Assert
    assert len(outcome.takeaways[0]) == TAKEAWAY_LIMIT


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


def test_an_outcome_takeaways_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    takeaways = ["Salt early"]
    outcome = an_outcome(takeaways=takeaways)

    # Execute
    takeaways.append("Rest the meat")

    # Assert
    assert outcome == an_outcome(takeaways=("Salt early",))


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


def test_an_outcome_accepts_ids_of_the_maximum_length() -> None:
    # Execute
    outcome = an_outcome(id="x" * 40, item_id="y" * 40)

    # Assert
    assert (outcome.id, outcome.item_id) == ("x" * 40, "y" * 40)


def test_an_outcome_completed_on_a_datetime_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="completed_on must be a date, not a datetime"):
        an_outcome(completed_on=BASE)


def test_an_outcome_with_naive_recorded_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="recorded_at"):
        an_outcome(recorded_at=NAIVE)


def test_with_notes_replaces_the_notes_and_takeaways() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    edited = outcome.with_notes("Better the second time", ("Less salt",), LATER)

    # Assert
    assert (edited.notes, edited.takeaways) == ("Better the second time", ("Less salt",))


def test_with_notes_stamps_edited_at_with_now() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    edited = outcome.with_notes("Better", (), LATER)

    # Assert
    assert edited.edited_at == LATER


def test_with_notes_keeps_recorded_at() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    edited = outcome.with_notes("Better", (), LATER)

    # Assert
    assert edited.recorded_at == BASE


def test_with_notes_changes_nothing_but_notes_takeaways_and_edited_at() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    edited = outcome.with_notes("Better", ("Less salt",), LATER)

    # Assert
    assert edited == an_outcome(notes="Better", takeaways=("Less salt",), edited_at=LATER)


def test_with_notes_keeps_id_item_id_completed_on_and_rating() -> None:
    # Setup
    outcome = an_outcome(id="o7", item_id="i7", rating=2)

    # Execute
    edited = outcome.with_notes("Better", (), LATER)

    # Assert
    assert (edited.id, edited.item_id, edited.completed_on, edited.rating) == (
        "o7",
        "i7",
        COMPLETED_ON,
        2,
    )


def test_with_notes_leaves_the_original_outcome_unchanged() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    outcome.with_notes("Better", ("Less salt",), LATER)

    # Assert
    assert outcome == an_outcome()


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


def test_an_outcome_is_not_edited_until_it_is_given_an_edited_at() -> None:
    # Execute
    outcome = an_outcome()

    # Assert
    assert outcome.edited_at is None


def test_an_outcome_with_naive_edited_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="edited_at"):
        an_outcome(edited_at=NAIVE)


def test_an_outcome_edited_before_it_was_recorded_is_accepted() -> None:
    # Execute
    outcome = an_outcome(recorded_at=LATER, edited_at=BASE)

    # Assert
    assert outcome.edited_at == BASE


def test_with_notes_dated_before_the_outcome_was_recorded_is_accepted() -> None:
    # Setup
    outcome = an_outcome(recorded_at=LATER)

    # Execute
    edited = outcome.with_notes("Better", (), BASE)

    # Assert
    assert edited.edited_at == BASE


def test_with_notes_without_takeaways_keeps_the_current_takeaways() -> None:
    # Setup
    outcome = an_outcome(takeaways=("Salt early", "Rest dough"))

    # Execute
    edited = outcome.with_notes("Better", None, LATER)

    # Assert
    assert edited.takeaways == ("Salt early", "Rest dough")


def test_with_notes_without_takeaways_still_replaces_the_notes() -> None:
    # Execute
    edited = an_outcome().with_notes("Better", None, LATER)

    # Assert
    assert edited.notes == "Better"


def test_with_notes_without_notes_keeps_the_current_notes() -> None:
    # Setup
    outcome = an_outcome(notes="Great")

    # Execute
    edited = outcome.with_notes(None, ("Less salt",), LATER)

    # Assert
    assert (edited.notes, edited.takeaways) == ("Great", ("Less salt",))


def test_an_outcome_with_a_rating_is_rated() -> None:
    # Execute
    outcome = an_outcome(rating=4)

    # Assert
    assert outcome.is_rated is True


def test_an_outcome_without_a_rating_is_not_rated() -> None:
    # Execute
    outcome = an_outcome(rating=None)

    # Assert
    assert outcome.is_rated is False
