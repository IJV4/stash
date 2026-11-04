import pytest

from stash.domain import require_max_length


def test_text_at_the_limit_is_accepted() -> None:
    # Execute
    result = require_max_length("note", "abc", 3)

    # Assert
    assert result is None


def test_text_over_the_limit_raises_value_error_naming_the_argument_and_limit() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="note must be at most 3 characters"):
        require_max_length("note", "abcd", 3)
