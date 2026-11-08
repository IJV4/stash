from builders import an_item

from stash.capture.wording import LINE_LIMIT
from stash.domain import Pick


def a_pick(title: str = "Dune", reason: str = "A long evening read") -> Pick:
    return Pick(an_item(title=title), reason)


def test_the_line_limit_is_three_hundred_characters() -> None:
    # Assert
    assert LINE_LIMIT == 300
