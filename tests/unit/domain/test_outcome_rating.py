import pytest
from builders import LATER, NAIVE, an_outcome

OUT_OF_RANGE_RATINGS = [0, 6]


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
