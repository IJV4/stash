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
