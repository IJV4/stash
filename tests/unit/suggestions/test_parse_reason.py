import pytest
from suggestion_builders import DUNE_ID, a_raw_pick

from stash.domain import SUGGESTION_REASON_LIMIT
from stash.suggestions import parse_suggestions

NOT_A_STRING = [None, 3, ["Fits"], {"a": "b"}, True]
BLANK = ["", "   ", "\n\t", "\x07\x07"]


def reasons_of(*raw_picks: object) -> list[str]:
    return [s.reason for s in parse_suggestions({"picks": list(raw_picks)}, {DUNE_ID}, 3)]


@pytest.mark.parametrize("value", NOT_A_STRING, ids=repr)
def test_a_reason_that_is_not_text_drops_the_pick(value: object) -> None:
    # Execute
    reasons = reasons_of(a_raw_pick(reason=value))

    # Assert
    assert reasons == []


@pytest.mark.parametrize("value", BLANK, ids=repr)
def test_a_blank_reason_drops_the_pick(value: str) -> None:
    # Execute
    reasons = reasons_of(a_raw_pick(reason=value))

    # Assert
    assert reasons == []


def test_a_reason_over_the_limit_is_cut_to_the_limit() -> None:
    # Execute
    reasons = reasons_of(a_raw_pick(reason="r" * (SUGGESTION_REASON_LIMIT + 50)))

    # Assert
    assert reasons == ["r" * SUGGESTION_REASON_LIMIT]


def test_whitespace_in_a_reason_is_collapsed() -> None:
    # Execute
    reasons = reasons_of(a_raw_pick(reason="A  quiet\n\nread"))

    # Assert
    assert reasons == ["A quiet read"]


def test_a_control_character_in_a_reason_is_replaced_by_a_space() -> None:
    # Execute
    reasons = reasons_of(a_raw_pick(reason="Cosy\x1b[31mred"))

    # Assert
    assert reasons == ["Cosy [31mred"]
