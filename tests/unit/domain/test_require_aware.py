from datetime import UTC, datetime

import pytest

from stash.domain import require_aware


def test_a_timezone_aware_moment_is_accepted() -> None:
    # Execute
    result = require_aware("moment", datetime(2026, 11, 2, 12, 0, tzinfo=UTC))

    # Assert
    assert result is None


def test_a_naive_moment_raises_value_error_naming_the_argument() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="deadline must be timezone-aware"):
        require_aware("deadline", datetime(2026, 11, 2, 12, 0))
