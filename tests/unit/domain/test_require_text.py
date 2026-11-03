import pytest

from stash.domain import require_text


def test_non_blank_text_is_accepted() -> None:
    # Execute
    result = require_text("name", "doctor")

    # Assert
    assert result is None


def test_empty_text_raises_value_error_naming_the_argument() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="name must not be blank"):
        require_text("name", "")


def test_whitespace_only_text_raises_value_error_naming_the_argument() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="detail must not be blank"):
        require_text("detail", " \t\n")
