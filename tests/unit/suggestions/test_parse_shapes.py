import pytest
from suggestion_builders import DUNE_ID, a_raw_pick

from stash.suggestions import Suggestion, parse_suggestions

ALLOWED = {DUNE_ID, "ramen"}
NOT_A_LIST = ["dune", {"item_id": DUNE_ID}, None, 3]
NOT_A_DICT = ["dune", 3, None, [DUNE_ID, "reason"]]


def test_an_answer_without_picks_suggests_nothing() -> None:
    # Execute
    suggestions = parse_suggestions({}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


@pytest.mark.parametrize("value", NOT_A_LIST, ids=repr)
def test_an_answer_whose_picks_are_not_a_list_suggests_nothing(value: object) -> None:
    # Execute
    suggestions = parse_suggestions({"picks": value}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


def test_an_empty_list_of_picks_suggests_nothing() -> None:
    # Execute
    suggestions = parse_suggestions({"picks": []}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


@pytest.mark.parametrize("entry", NOT_A_DICT, ids=repr)
def test_a_pick_that_is_not_an_object_is_dropped(entry: object) -> None:
    # Execute
    suggestions = parse_suggestions({"picks": [entry]}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


def test_a_pick_missing_its_item_id_is_dropped() -> None:
    # Execute
    suggestions = parse_suggestions({"picks": [{"reason": "Fits"}]}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


def test_a_pick_missing_its_reason_is_dropped() -> None:
    # Execute
    suggestions = parse_suggestions({"picks": [{"item_id": DUNE_ID}]}, ALLOWED, 3)

    # Assert
    assert suggestions == ()


def test_a_usable_pick_becomes_a_suggestion() -> None:
    # Execute
    suggestions = parse_suggestions({"picks": [a_raw_pick(DUNE_ID, "Fits")]}, ALLOWED, 3)

    # Assert
    assert suggestions == (Suggestion(DUNE_ID, "Fits"),)


def test_picks_keep_the_order_the_model_gave() -> None:
    # Setup
    raw = {"picks": [a_raw_pick("ramen"), a_raw_pick(DUNE_ID)]}

    # Execute
    suggestions = parse_suggestions(raw, ALLOWED, 3)

    # Assert
    assert [suggestion.item_id for suggestion in suggestions] == ["ramen", DUNE_ID]
