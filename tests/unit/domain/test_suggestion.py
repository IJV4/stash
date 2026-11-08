import pytest
from builders import an_item

from stash.domain import SUGGESTION_REASON_LIMIT, Pick, require_reason


def test_the_reason_limit_is_two_hundred_characters() -> None:
    # Assert
    assert SUGGESTION_REASON_LIMIT == 200


@pytest.mark.parametrize("reason", ["", "   ", "\n\t"], ids=repr)
def test_a_pick_with_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        Pick(an_item(), reason)


@pytest.mark.parametrize("reason", ["", "  "], ids=repr)
def test_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        require_reason(reason)
