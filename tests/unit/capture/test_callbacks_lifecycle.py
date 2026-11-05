import pytest
from builders import HEX_ID

from stash.capture.callbacks import (
    RATING_ARGUMENTS,
    FixAction,
    FixKind,
    KeepChoice,
    rating_for,
)

ACTIONS_AND_WIRE = [
    (FixAction(FixKind.DONE, "i1"), "stash:d:i1"),
    (FixAction(FixKind.RATE, "o1", "4"), "stash:r:o1:4"),
    (FixAction(FixKind.KEEP, "i1", "1"), "stash:k:i1:1"),
    (FixAction(FixKind.KEEP, "i1", "0"), "stash:k:i1:0"),
]


@pytest.mark.parametrize(("action", "wire"), ACTIONS_AND_WIRE)
def test_each_completion_kind_encodes_to_its_stable_wire_format(
    action: FixAction, wire: str
) -> None:
    # Execute / Assert
    assert action.encode() == wire


@pytest.mark.parametrize(("action", "wire"), ACTIONS_AND_WIRE)
def test_each_completion_wire_string_parses_back_to_its_action(
    action: FixAction, wire: str
) -> None:
    # Execute / Assert
    assert FixAction.parse(wire) == action


@pytest.mark.parametrize(
    "wire",
    [
        f"stash:d:{HEX_ID}",
        f"stash:r:{HEX_ID}:5",
        f"stash:k:{HEX_ID}:1",
        f"stash:k:{HEX_ID}:0",
    ],
)
def test_a_frozen_sample_of_every_completion_wire_format_parses_back_to_the_same_string(
    wire: str,
) -> None:
    # Execute
    parsed = FixAction.parse(wire)

    # Assert
    assert parsed is not None and parsed.encode() == wire


@pytest.mark.parametrize(
    "data",
    [
        "stash:d:i1:1",
        "stash:d:i1:extra",
        "stash:d:",
        "stash:r:o1",
        "stash:r:o1:",
        "stash:r::4",
        "stash:r:o1:4:extra",
        "stash:k:i1",
        "stash:k:i1:",
        "stash:k::1",
        "stash:k:i1:1:extra",
    ],
)
def test_parse_returns_none_when_a_completion_kind_has_the_wrong_argument_presence(
    data: str,
) -> None:
    # Execute / Assert
    assert FixAction.parse(data) is None


@pytest.mark.parametrize(
    ("kind", "argument"),
    [
        (FixKind.DONE, "1"),
        (FixKind.RATE, None),
        (FixKind.KEEP, None),
    ],
)
def test_a_completion_action_with_the_wrong_argument_presence_is_refused(
    kind: FixKind, argument: str | None
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(kind, "i1", argument)


@pytest.mark.parametrize(
    ("kind", "takes_argument"),
    [
        (FixKind.DONE, False),
        (FixKind.RATE, True),
        (FixKind.KEEP, True),
        (FixKind.SET_TYPE, True),
        (FixKind.SET_STAGE, True),
        (FixKind.TYPE_MENU, False),
        (FixKind.STAGE_MENU, False),
        (FixKind.QUESTION, False),
    ],
)
def test_only_the_kinds_that_carry_a_choice_take_an_argument(
    kind: FixKind, takes_argument: bool
) -> None:
    # Execute / Assert
    assert kind.takes_argument is takes_argument


def test_choosing_to_keep_means_kept() -> None:
    # Execute / Assert
    assert KeepChoice.KEEP.kept is True


def test_choosing_not_to_keep_means_not_kept() -> None:
    # Execute / Assert
    assert KeepChoice.NOT_KEEPING.kept is False


def test_the_keep_choices_travel_as_one_and_zero() -> None:
    # Execute / Assert
    assert (KeepChoice.KEEP.value, KeepChoice.NOT_KEEPING.value) == ("1", "0")


def test_the_rating_arguments_map_each_digit_string_to_its_rating() -> None:
    # Execute / Assert
    assert dict(RATING_ARGUMENTS) == {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def test_no_argument_is_no_rating() -> None:
    # Execute / Assert
    assert rating_for(None) is None


@pytest.mark.parametrize(("argument", "rating"), [("1", 1), ("2", 2), ("3", 3), ("4", 4), ("5", 5)])
def test_a_single_digit_from_one_to_five_is_that_rating(argument: str, rating: int) -> None:
    # Execute / Assert
    assert rating_for(argument) == rating


@pytest.mark.parametrize("argument", ["0", "6", "x", "+3", "٣", "", " 3", "03"])
def test_an_argument_that_is_not_a_single_rating_digit_is_no_rating(argument: str) -> None:
    # Execute / Assert
    assert rating_for(argument) is None
