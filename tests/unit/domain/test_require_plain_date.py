from datetime import datetime

import pytest
from builders import BASE

from stash.domain import require_plain_date


def test_a_datetime_raises_value_error_naming_the_argument() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="day must be a date, not a datetime"):
        require_plain_date("day", BASE)


def test_a_naive_datetime_raises_value_error_too() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="day must be a date, not a datetime"):
        require_plain_date("day", datetime(2026, 11, 2, 12, 0))
