import pytest

from stash.capture.callbacks import FixAction, FixKind

PLANNING_KINDS = [FixKind.ACCEPT_STEPS, FixKind.SKIP_STEPS, FixKind.STEP_DONE]


@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_a_planning_action_with_an_argument_is_refused(kind: FixKind) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(kind, "i1", "1")


@pytest.mark.parametrize("kind", PLANNING_KINDS)
def test_parse_returns_none_when_a_planning_wire_string_carries_an_argument(kind: FixKind) -> None:
    # Execute / Assert
    assert FixAction.parse(f"stash:{kind.value}:i1:1") is None


def test_no_two_fix_kinds_share_a_wire_value() -> None:
    # Execute
    wire_values = [kind.value for kind in FixKind.__members__.values()]

    # Assert
    assert len(set(wire_values)) == len(FixKind.__members__)
