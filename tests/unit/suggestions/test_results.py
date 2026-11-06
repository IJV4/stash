import pytest
from builders import MAX_LENGTH_ID, UNSAFE_WIRE_IDS, an_item

from stash.domain import SUGGESTION_REASON_LIMIT, Pick
from stash.suggestions.results import (
    CONTEXT_LIMIT,
    SUGGESTION_LIMIT,
    ContextTooLong,
    Picked,
    Suggestion,
    Unavailable,
)


def test_a_suggestion_names_an_item_and_the_reason_it_fits() -> None:
    # Execute
    suggestion = Suggestion("dune", "A quiet read")

    # Assert
    assert (suggestion.item_id, suggestion.reason) == ("dune", "A quiet read")


@pytest.mark.parametrize("item_id", UNSAFE_WIRE_IDS, ids=repr)
def test_a_suggestion_with_an_unsafe_item_id_is_refused(item_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item id"):
        Suggestion(item_id, "A quiet read")


def test_a_suggestion_with_an_item_id_of_the_maximum_length_is_accepted() -> None:
    # Execute
    suggestion = Suggestion(MAX_LENGTH_ID, "A quiet read")

    # Assert
    assert suggestion.item_id == MAX_LENGTH_ID


@pytest.mark.parametrize("reason", ["", "  ", "\n"], ids=repr)
def test_a_suggestion_with_a_blank_reason_is_refused(reason: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason"):
        Suggestion("dune", reason)


def test_a_suggestion_with_a_reason_over_the_limit_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason must be at most 200 characters"):
        Suggestion("dune", "r" * (SUGGESTION_REASON_LIMIT + 1))


def test_a_suggestion_with_a_reason_of_exactly_the_limit_is_accepted() -> None:
    # Execute
    suggestion = Suggestion("dune", "r" * SUGGESTION_REASON_LIMIT)

    # Assert
    assert len(suggestion.reason) == SUGGESTION_REASON_LIMIT


def test_picked_holds_the_picks_in_order() -> None:
    # Setup
    picks = (Pick(an_item(id="a"), "first"), Pick(an_item(id="b"), "second"))

    # Execute
    picked = Picked(picks)

    # Assert
    assert picked.picks == picks


def test_all_unavailable_answers_are_equal() -> None:
    # Assert
    assert Unavailable() == Unavailable()


def test_unavailable_is_not_an_empty_picked() -> None:
    # Assert
    assert Unavailable() != Picked(())


def test_the_context_limit_is_five_hundred_characters() -> None:
    # Assert
    assert CONTEXT_LIMIT == 500


def test_a_context_too_long_error_names_the_limit() -> None:
    # Execute
    error = ContextTooLong()

    # Assert
    assert str(error) == "context must be at most 500 characters"


def test_a_context_too_long_error_is_a_value_error() -> None:
    # Assert
    assert issubclass(ContextTooLong, ValueError)


def test_the_suggestion_limit_is_three() -> None:
    # Assert
    assert SUGGESTION_LIMIT == 3
