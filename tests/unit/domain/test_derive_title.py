from stash.domain.item import derive_title


def test_derive_title_takes_the_first_non_empty_line_with_whitespace_collapsed() -> None:
    # Assert
    assert derive_title("  \n Ramen   in Shibuya \n more") == "Ramen in Shibuya"


def test_derive_title_collapses_tabs_and_inner_runs_of_whitespace() -> None:
    # Assert
    assert derive_title("Ramen\t\tin   Shibuya") == "Ramen in Shibuya"


def test_derive_title_leaves_a_short_single_line_unchanged() -> None:
    # Assert
    assert derive_title("Ramen in Shibuya") == "Ramen in Shibuya"


def test_derive_title_of_empty_text_is_untitled() -> None:
    # Assert
    assert derive_title("") == "Untitled"


def test_derive_title_of_whitespace_only_text_is_untitled() -> None:
    # Assert
    assert derive_title(" \n\t \n  ") == "Untitled"


def test_derive_title_leaves_text_of_exactly_120_characters_unchanged() -> None:
    # Setup
    text = "x" * 120

    # Assert
    assert derive_title(text) == text


def test_derive_title_of_121_characters_is_truncated_to_120_ending_with_ellipsis() -> None:
    # Assert
    assert derive_title("x" * 121) == "x" * 119 + "…"


def test_derive_title_of_long_text_has_length_120() -> None:
    # Assert
    assert len(derive_title("x" * 200)) == 120


def test_derive_title_of_long_text_ends_with_ellipsis() -> None:
    # Assert
    assert derive_title("x" * 200).endswith("…")


def test_derive_title_truncates_only_the_first_non_empty_line() -> None:
    # Assert
    assert derive_title("\n" + "y" * 150 + "\nshort") == "y" * 119 + "…"


def test_derive_title_collapses_non_breaking_spaces() -> None:
    # Assert
    assert derive_title("Ramen\u00a0\u00a0in Shibuya") == "Ramen in Shibuya"
