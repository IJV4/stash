from builders import an_item

from stash.capture import pick_line
from stash.capture.wording import LINE_LIMIT
from stash.domain import Pick


def a_pick(title: str = "Dune", reason: str = "A long evening read") -> Pick:
    return Pick(an_item(title=title), reason)


def test_a_pick_reads_as_a_bullet_the_title_and_the_reason() -> None:
    # Execute
    line = pick_line(a_pick())

    # Assert
    assert line == "• Dune — A long evening read"


def test_whitespace_in_the_title_and_the_reason_is_collapsed() -> None:
    # Execute
    line = pick_line(a_pick(title="Dune\n\n  Messiah", reason="Short\tand   sweet"))

    # Assert
    assert line == "• Dune Messiah — Short and sweet"


def test_a_control_character_in_the_reason_is_not_printed() -> None:
    # Execute
    line = pick_line(a_pick(reason="Cosy\x07evening"))

    # Assert
    assert line == "• Dune — Cosy evening"


def test_a_line_longer_than_the_limit_is_cut_to_the_limit() -> None:
    # Execute
    line = pick_line(a_pick(title="T" * 150, reason="r" * 200))

    # Assert
    assert len(line) == LINE_LIMIT


def test_the_line_limit_is_three_hundred_characters() -> None:
    # Assert
    assert LINE_LIMIT == 300


def test_a_line_within_the_limit_is_kept_whole() -> None:
    # Execute
    line = pick_line(a_pick(title="T" * 50, reason="r" * 200))

    # Assert
    assert line == f"• {'T' * 50} — {'r' * 200}"
