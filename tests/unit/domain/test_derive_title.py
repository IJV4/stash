from stash.domain.item import derive_title


def test_derive_title_takes_the_first_non_empty_line_with_whitespace_collapsed() -> None:
    # Assert
    assert derive_title("  \n Ramen   in Shibuya \n more") == "Ramen in Shibuya"


def test_derive_title_of_whitespace_only_text_is_untitled() -> None:
    # Assert
    assert derive_title(" \n\t \n  ") == "Untitled"


def test_derive_title_truncates_only_the_first_non_empty_line() -> None:
    # Assert
    assert derive_title("\n" + "y" * 150 + "\nshort") == "y" * 119 + "…"


def test_derive_title_skips_a_first_line_of_only_control_characters() -> None:
    # Assert
    assert derive_title("\x1b\x07\nRamen in Shibuya") == "Ramen in Shibuya"


def test_derive_title_keeps_a_zero_width_joiner_inside_an_emoji_sequence() -> None:
    # Assert
    assert derive_title("👩\u200d💻 Coding") == "👩\u200d💻 Coding"


def test_derive_title_skips_a_first_line_of_only_joiners_and_spaces() -> None:
    # Assert
    assert derive_title("\u200d \u200c\nRamen in Shibuya") == "Ramen in Shibuya"
