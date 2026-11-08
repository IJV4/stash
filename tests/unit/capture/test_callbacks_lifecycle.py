import pytest

from stash.capture.callbacks import (
    RATING_ARGUMENTS,
    FixAction,
    FixKind,
    KeepChoice,
)


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


def test_the_keep_choices_travel_as_one_and_zero() -> None:
    # Execute / Assert
    assert (KeepChoice.KEEP.value, KeepChoice.NOT_KEEPING.value) == ("1", "0")


def test_the_rating_arguments_map_each_digit_string_to_its_rating() -> None:
    # Execute / Assert
    assert dict(RATING_ARGUMENTS) == {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
