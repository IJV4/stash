import pytest

from stash.domain.wire import MAX_ID_LENGTH, is_wire_safe, require_wire_safe_id


@pytest.mark.parametrize("part", ["c1", "recipe", "want_to", "a" * 200, "0123456789abcdef"])
def test_a_printable_colon_free_part_without_whitespace_is_wire_safe(part: str) -> None:
    # Execute / Assert
    assert is_wire_safe(part) is True


@pytest.mark.parametrize(
    "part",
    ["", " ", "a b", "a\tb", "a\nb", "a:b", ":", "a\x07b", "a\x00b", "a\u00a0b", "a\u200bb", "é"],
)
def test_a_blank_spaced_non_printable_or_colon_part_is_not_wire_safe(part: str) -> None:
    # Execute / Assert
    assert is_wire_safe(part) is False


def test_an_id_of_exactly_the_maximum_length_is_accepted() -> None:
    # Execute / Assert
    require_wire_safe_id("id", "a" * MAX_ID_LENGTH)


def test_an_id_one_character_over_the_maximum_length_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=f"id must be at most {MAX_ID_LENGTH} characters"):
        require_wire_safe_id("id", "a" * (MAX_ID_LENGTH + 1))


@pytest.mark.parametrize("value", ["", "  ", "chat:42", "two words", "bell\x07"])
def test_an_id_that_is_not_wire_safe_raises_value_error(value: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="id must be non-blank, printable"):
        require_wire_safe_id("id", value)


def test_forty_non_ascii_characters_are_refused_because_they_would_exceed_the_byte_limit() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="id must be non-blank, printable"):
        require_wire_safe_id("id", "é" * MAX_ID_LENGTH)
