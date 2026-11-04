import pytest
from builders import (
    LATER,
    an_item,
    an_item_at,
)

from stash.domain.item import DROP_REASON_LIMIT, Stage


@pytest.mark.parametrize("stage", list(Stage))
def test_dropped_moves_an_item_to_dropped_from_every_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    dropped = item.dropped("Not for me", LATER)

    # Assert
    assert dropped.stage is Stage.DROPPED


def test_dropped_records_the_reason() -> None:
    # Setup
    item = an_item()

    # Execute
    dropped = item.dropped("Not for me", LATER)

    # Assert
    assert dropped.drop_reason == "Not for me"


def test_dropped_without_a_reason_leaves_the_drop_reason_empty() -> None:
    # Setup
    item = an_item()

    # Execute
    dropped = item.dropped(None, LATER)

    # Assert
    assert dropped.drop_reason is None


def test_dropped_accepts_a_reason_of_the_maximum_length() -> None:
    # Setup
    item = an_item()

    # Execute
    dropped = item.dropped("r" * DROP_REASON_LIMIT, LATER)

    # Assert
    assert dropped.drop_reason == "r" * DROP_REASON_LIMIT


def test_dropped_with_a_reason_over_the_maximum_length_raises_value_error() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(
        ValueError, match=f"drop_reason must be at most {DROP_REASON_LIMIT} characters"
    ):
        item.dropped("r" * (DROP_REASON_LIMIT + 1), LATER)


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_dropped_with_a_blank_reason_raises_value_error(blank: str) -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="drop_reason must not be blank"):
        item.dropped(blank, LATER)


def test_dropping_an_already_dropped_item_replaces_the_reason() -> None:
    # Setup
    item = an_item(stage=Stage.DROPPED, drop_reason="Too far")

    # Execute
    dropped = item.dropped("Closed down", LATER)

    # Assert
    assert dropped.drop_reason == "Closed down"


def test_dropping_an_already_dropped_item_without_a_reason_clears_the_reason() -> None:
    # Setup
    item = an_item(stage=Stage.DROPPED, drop_reason="Too far")

    # Execute
    dropped = item.dropped(None, LATER)

    # Assert
    assert dropped.drop_reason is None


def test_dropped_changes_nothing_but_stage_drop_reason_and_updated_at() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO, tags=("food",), parent_id="p1")

    # Execute
    dropped = item.dropped("Not for me", LATER)

    # Assert
    assert dropped == an_item(
        stage=Stage.DROPPED,
        drop_reason="Not for me",
        tags=("food",),
        parent_id="p1",
        updated_at=LATER,
    )


def test_dropped_does_not_change_whether_a_done_item_is_kept() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, kept=True)

    # Execute
    dropped = item.dropped("Not for me", LATER)

    # Assert
    assert dropped.kept is True
