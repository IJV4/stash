import pytest
from builders import UNSAFE_WIRE_IDS

from stash.suggestions.results import (
    CONTEXT_LIMIT,
    SUGGESTION_LIMIT,
    ContextTooLong,
    Picked,
    Suggestion,
    Unavailable,
)


@pytest.mark.parametrize("item_id", UNSAFE_WIRE_IDS, ids=repr)
def test_a_suggestion_with_an_unsafe_item_id_is_refused(item_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item id"):
        Suggestion(item_id, "A quiet read")


@pytest.mark.parametrize("reason", ["", "  ", "\n"], ids=repr)
def test_a_suggestion_with_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        Suggestion("dune", reason)


def test_all_unavailable_answers_are_equal() -> None:
    # Assert
    assert Unavailable() == Unavailable()


def test_unavailable_is_not_an_empty_picked() -> None:
    # Assert
    assert Unavailable() != Picked(())


def test_the_context_limit_is_five_hundred_characters() -> None:
    # Assert
    assert CONTEXT_LIMIT == 500


def test_a_context_too_long_error_is_a_value_error() -> None:
    # Assert
    assert issubclass(ContextTooLong, ValueError)


def test_the_suggestion_limit_is_three() -> None:
    # Assert
    assert SUGGESTION_LIMIT == 3
