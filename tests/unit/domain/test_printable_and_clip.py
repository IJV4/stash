import pytest

from stash.domain import printable_and_clip


def test_whitespace_is_still_collapsed_to_single_spaces() -> None:
    # Execute / Assert
    assert printable_and_clip("a \n\t b", 50) == "a b"


def test_an_escape_character_is_replaced_by_a_space() -> None:
    # Execute / Assert
    assert printable_and_clip("screen\x1b[2Jcleared", 50) == "screen [2Jcleared"


def test_escape_and_bell_characters_of_a_clipboard_write_are_replaced_by_spaces() -> None:
    # Execute / Assert
    assert printable_and_clip("copy\x1b]52;c;ZmFrZQ==\x07done", 50) == "copy ]52;c;ZmFrZQ== done"


def test_a_bidi_override_character_is_replaced_by_a_space() -> None:
    # Execute / Assert
    assert printable_and_clip("abc\u202edef", 50) == "abc def"


def test_replacing_a_character_between_spaces_leaves_no_double_space() -> None:
    # Execute / Assert
    assert printable_and_clip("a \x1b b", 50) == "a b"


def test_printable_non_ascii_text_is_kept() -> None:
    # Execute / Assert
    assert printable_and_clip("café 日本", 50) == "café 日本"


def test_clipping_counts_only_the_characters_that_remain_after_collapsing() -> None:
    # Execute / Assert
    assert printable_and_clip("\x1b" * 10 + "abcdef", 4) == "abcd"


def test_a_line_break_between_words_becomes_a_space_rather_than_merging_them() -> None:
    # Execute / Assert
    assert printable_and_clip("a\nb", 50) == "a b"


def test_a_control_character_between_tokens_keeps_them_apart() -> None:
    # Execute / Assert
    assert printable_and_clip("ab\x00cd", 50) == "ab cd"


def test_a_c1_control_character_is_replaced_by_a_space() -> None:
    # Execute / Assert
    assert printable_and_clip("move\x9b2J", 50) == "move 2J"


@pytest.mark.parametrize("separator", ["\u2028", "\u2029"])
def test_a_unicode_line_or_paragraph_separator_becomes_a_space(separator: str) -> None:
    # Execute / Assert
    assert printable_and_clip(f"one{separator}two", 50) == "one two"
