import pytest
from builders import HEX_ID, MAX_LENGTH_ID

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT, FixAction, FixKind

PLANNING_ACTIONS_AND_WIRE = [
    (FixAction(FixKind.ACCEPT_STEPS, "i1"), "stash:a:i1"),
    (FixAction(FixKind.SKIP_STEPS, "i1"), "stash:n:i1"),
    (FixAction(FixKind.STEP_DONE, "s1"), "stash:x:s1"),
]
PLANNING_KINDS = [FixKind.ACCEPT_STEPS, FixKind.SKIP_STEPS, FixKind.STEP_DONE]


@pytest.mark.parametrize(("action", "wire"), PLANNING_ACTIONS_AND_WIRE)
def test_each_planning_kind_encodes_to_its_stable_wire_format(action: FixAction, wire: str) -> None:
    # Execute / Assert
    assert action.encode() == wire


@pytest.mark.parametrize(("action", "wire"), PLANNING_ACTIONS_AND_WIRE)
def test_each_planning_wire_string_parses_back_to_its_action(action: FixAction, wire: str) -> None:
    # Execute / Assert
    assert FixAction.parse(wire) == action


@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_a_planning_kind_takes_no_argument(kind: FixKind) -> None:
    # Execute / Assert
    assert kind.takes_argument is False


@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_a_planning_action_with_an_argument_is_refused(kind: FixKind) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(kind, "i1", "1")


@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_parse_returns_none_when_a_planning_wire_string_carries_an_argument(kind: FixKind) -> None:
    # Execute / Assert
    assert FixAction.parse(f"stash:{kind.value}:i1:1") is None


@pytest.mark.parametrize("subject_id", [HEX_ID, MAX_LENGTH_ID])
@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_a_planning_action_for_the_longest_ids_fits_the_telegram_callback_limit(
    kind: FixKind, subject_id: str
) -> None:
    # Execute
    data = FixAction(kind, subject_id).encode()

    # Assert
    assert len(data.encode("utf-8")) <= TELEGRAM_CALLBACK_LIMIT


def test_no_two_fix_kinds_share_a_wire_value() -> None:
    # Execute
    wire_values = [kind.value for kind in FixKind.__members__.values()]

    # Assert
    assert len(set(wire_values)) == len(FixKind.__members__)
