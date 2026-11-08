from datetime import date, datetime
from typing import Any

import pytest
from builders import LATER, NAIVE, an_item

NEW_DATE = date(2026, 12, 25)
A_DATETIME: Any = datetime(2026, 12, 25, 9, 0)


def test_rescheduling_to_a_datetime_is_refused() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="date must be a date, not a datetime"):
        item.rescheduled(A_DATETIME, LATER)


def test_rescheduling_with_a_naive_now_is_refused() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at must be timezone-aware"):
        item.rescheduled(NEW_DATE, NAIVE)
