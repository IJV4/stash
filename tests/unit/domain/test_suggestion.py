import pytest
from builders import an_item

from stash.domain import SUGGESTION_REASON_LIMIT, Pick, require_reason


def test_a_pick_pairs_an_item_with_the_reason_it_fits() -> None:
    # Setup
    item = an_item(title="Dune")

    # Execute
    pick = Pick(item, "A long evening read")

    # Assert
    assert (pick.item, pick.reason) == (item, "A long evening read")


def test_the_reason_limit_is_two_hundred_characters() -> None:
    # Assert
    assert SUGGESTION_REASON_LIMIT == 200


@pytest.mark.parametrize("reason", ["", "   ", "\n\t"], ids=repr)
def test_a_pick_with_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        Pick(an_item(), reason)


def test_a_pick_with_a_reason_of_exactly_the_limit_is_accepted() -> None:
    # Execute
    pick = Pick(an_item(), "r" * SUGGESTION_REASON_LIMIT)

    # Assert
    assert len(pick.reason) == SUGGESTION_REASON_LIMIT


def test_a_pick_with_a_reason_over_the_limit_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason must be at most 200 characters"):
        Pick(an_item(), "r" * (SUGGESTION_REASON_LIMIT + 1))


@pytest.mark.parametrize("reason", ["", "  "], ids=repr)
def test_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        require_reason(reason)


def test_a_reason_over_the_limit_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason must be at most 200 characters"):
        require_reason("r" * (SUGGESTION_REASON_LIMIT + 1))


def test_a_reason_of_exactly_the_limit_is_accepted() -> None:
    # Execute
    outcome = require_reason("r" * SUGGESTION_REASON_LIMIT)

    # Assert
    assert outcome is None
