import pytest
from builders import (
    LATER,
    an_item,
)

from stash.domain.item import DROP_REASON_LIMIT


def test_dropped_with_a_reason_over_the_maximum_length_raises_value_error() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(
        ValueError, match=f"drop_reason must be at most {DROP_REASON_LIMIT} characters"
    ):
        item.dropped("r" * (DROP_REASON_LIMIT + 1), LATER)


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_dropped_with_a_blank_reason_raises_value_error(blank: str) -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="drop_reason must not be blank"):
        item.dropped(blank, LATER)
