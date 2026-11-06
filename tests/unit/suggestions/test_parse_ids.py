import pytest
from suggestion_builders import DUNE_ID, a_raw_pick

from stash.suggestions import parse_suggestions

ALLOWED = {DUNE_ID, "ramen"}
NOT_A_STRING = [None, 3, ["dune"], {"a": "b"}, True]


def ids_of(*raw_picks: object, limit: int = 3) -> list[str]:
    return [s.item_id for s in parse_suggestions({"picks": list(raw_picks)}, ALLOWED, limit)]


def test_an_id_that_is_not_among_the_candidates_is_dropped() -> None:
    # Execute
    ids = ids_of(a_raw_pick("invented"), a_raw_pick(DUNE_ID))

    # Assert
    assert ids == [DUNE_ID]


def test_an_id_differing_only_in_case_is_not_a_candidate() -> None:
    # Execute
    ids = ids_of(a_raw_pick("Dune"))

    # Assert
    assert ids == []


def test_a_repeated_id_is_kept_once_with_its_first_reason() -> None:
    # Setup
    raw = {"picks": [a_raw_pick(DUNE_ID, "first"), a_raw_pick(DUNE_ID, "second")]}

    # Execute
    suggestions = parse_suggestions(raw, ALLOWED, 3)

    # Assert
    assert [suggestion.reason for suggestion in suggestions] == ["first"]


@pytest.mark.parametrize("value", NOT_A_STRING, ids=repr)
def test_an_id_that_is_not_text_is_dropped(value: object) -> None:
    # Execute
    ids = ids_of(a_raw_pick(item_id=value))

    # Assert
    assert ids == []


def test_no_candidates_means_every_pick_is_dropped() -> None:
    # Execute
    suggestions = parse_suggestions({"picks": [a_raw_pick(DUNE_ID)]}, set(), 3)

    # Assert
    assert suggestions == ()
