import pytest
from builders import HEX_ID, MAX_LENGTH_ID

from stash.capture.callbacks import FixAction, FixKind


def test_the_not_happened_kind_travels_as_h() -> None:
    # Execute / Assert
    assert FixKind.NOT_HAPPENED.value == "h"


def test_not_happened_encodes_to_its_stable_wire_format() -> None:
    # Execute / Assert
    assert FixAction(FixKind.NOT_HAPPENED, "i1").encode() == "stash:h:i1"


def test_a_not_happened_wire_string_parses_back_to_its_action() -> None:
    # Execute / Assert
    assert FixAction.parse("stash:h:i1") == FixAction(FixKind.NOT_HAPPENED, "i1")


@pytest.mark.parametrize("subject_id", [HEX_ID, MAX_LENGTH_ID])
def test_a_not_happened_wire_string_for_the_longest_ids_parses_back_to_the_same_string(
    subject_id: str,
) -> None:
    # Setup
    wire = f"stash:h:{subject_id}"

    # Execute
    parsed = FixAction.parse(wire)

    # Assert
    assert parsed is not None and parsed.encode() == wire


def test_the_not_happened_kind_takes_no_argument() -> None:
    # Execute / Assert
    assert FixKind.NOT_HAPPENED.takes_argument is False


def test_a_not_happened_action_with_an_argument_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(FixKind.NOT_HAPPENED, "i1", "1")


def test_parse_returns_none_when_a_not_happened_wire_string_carries_an_argument() -> None:
    # Execute / Assert
    assert FixAction.parse("stash:h:i1:1") is None
