import pytest
from builders import BASE, LATER, NAIVE, an_outcome

OUT_OF_RANGE_RATINGS = [0, 6]


def test_with_rating_replaces_the_rating() -> None:
    # Setup
    outcome = an_outcome(rating=2)

    # Execute
    rated = outcome.with_rating(5, LATER)

    # Assert
    assert rated.rating == 5


def test_with_rating_stamps_edited_at_with_now() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    rated = outcome.with_rating(5, LATER)

    # Assert
    assert rated.edited_at == LATER


def test_with_rating_changes_nothing_but_rating_and_edited_at() -> None:
    # Setup
    outcome = an_outcome(rating=2)

    # Execute
    rated = outcome.with_rating(5, LATER)

    # Assert
    assert rated == an_outcome(rating=5, edited_at=LATER)


def test_with_rating_keeps_recorded_at() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    rated = outcome.with_rating(5, LATER)

    # Assert
    assert rated.recorded_at == BASE


def test_with_rating_leaves_the_original_outcome_unchanged() -> None:
    # Setup
    outcome = an_outcome()

    # Execute
    outcome.with_rating(5, LATER)

    # Assert
    assert outcome == an_outcome()


def test_with_rating_rates_an_outcome_that_had_no_rating() -> None:
    # Setup
    outcome = an_outcome(rating=None)

    # Execute
    rated = outcome.with_rating(3, LATER)

    # Assert
    assert rated.rating == 3


@pytest.mark.parametrize("rating", OUT_OF_RANGE_RATINGS)
def test_with_rating_outside_one_to_five_raises_value_error(rating: int) -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="rating"):
        outcome.with_rating(rating, LATER)


def test_with_rating_with_naive_now_raises_value_error() -> None:
    # Setup
    outcome = an_outcome()

    # Execute / Assert
    with pytest.raises(ValueError, match="edited_at"):
        outcome.with_rating(5, NAIVE)


def test_with_rating_dated_before_the_outcome_was_recorded_is_accepted() -> None:
    # Setup
    outcome = an_outcome(recorded_at=LATER)

    # Execute
    rated = outcome.with_rating(5, BASE)

    # Assert
    assert rated.edited_at == BASE
