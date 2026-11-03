from stash.domain import collapse_and_clip


def test_runs_of_whitespace_collapse_to_single_spaces() -> None:
    # Execute / Assert
    assert collapse_and_clip("a \n\t b   c", 50) == "a b c"


def test_surrounding_whitespace_is_stripped() -> None:
    # Execute / Assert
    assert collapse_and_clip("  hello  ", 50) == "hello"


def test_text_longer_than_the_limit_is_cut_to_the_limit_without_an_ellipsis() -> None:
    # Execute / Assert
    assert collapse_and_clip("abcdef", 4) == "abcd"


def test_text_exactly_at_the_limit_is_kept_whole() -> None:
    # Execute / Assert
    assert collapse_and_clip("abcd", 4) == "abcd"


def test_text_is_clipped_after_collapsing_whitespace() -> None:
    # Execute / Assert
    assert collapse_and_clip("ab    cd", 5) == "ab cd"


def test_clipping_leaves_no_trailing_space() -> None:
    # Execute / Assert
    assert collapse_and_clip("ab cd", 3) == "ab"


def test_blank_text_collapses_to_the_empty_string() -> None:
    # Execute / Assert
    assert collapse_and_clip(" \n\t ", 10) == ""
