import pytest
from builders import (
    LATER,
    NON_DONE_STAGES,
    an_item,
    an_item_at,
)

from stash.domain.item import Stage


def test_an_item_in_the_done_stage_is_done() -> None:
    # Setup
    item = an_item_at(Stage.DONE)

    # Execute / Assert
    assert item.is_done


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_an_item_in_any_other_stage_is_not_done(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    assert not item.is_done


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_completed_moves_the_item_to_done_from_every_other_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    completed = item.completed(LATER)

    # Assert
    assert completed.stage is Stage.DONE


def test_completed_on_a_done_item_raises_value_error() -> None:
    # Setup
    item = an_item(stage=Stage.DONE)

    # Execute / Assert
    with pytest.raises(ValueError, match="already done"):
        item.completed(LATER)


def test_completed_changes_nothing_but_stage_and_updated_at() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO, tags=("food",), people=("Ana",), parent_id="p1")

    # Execute
    completed = item.completed(LATER)

    # Assert
    assert completed == an_item(
        stage=Stage.DONE, tags=("food",), people=("Ana",), parent_id="p1", updated_at=LATER
    )


def test_completed_clears_the_drop_reason_of_a_dropped_item() -> None:
    # Setup
    item = an_item(stage=Stage.DROPPED, drop_reason="Not for me")

    # Execute
    completed = item.completed(LATER)

    # Assert
    assert completed.drop_reason is None


def test_completed_does_not_change_whether_the_item_is_kept() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO, kept=True)

    # Execute
    completed = item.completed(LATER)

    # Assert
    assert completed.kept is True


def test_reopened_moves_a_done_item_back_to_want_to() -> None:
    # Setup
    item = an_item(stage=Stage.DONE)

    # Execute
    reopened = item.reopened(LATER)

    # Assert
    assert reopened.stage is Stage.WANT_TO


def test_reopened_keeps_a_kept_item_kept() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, kept=True)

    # Execute
    reopened = item.reopened(LATER)

    # Assert
    assert reopened.kept is True


def test_reopened_changes_nothing_but_stage_and_updated_at() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, kept=True, tags=("food",), parent_id="p1")

    # Execute
    reopened = item.reopened(LATER)

    # Assert
    assert reopened == an_item(
        stage=Stage.WANT_TO, kept=True, tags=("food",), parent_id="p1", updated_at=LATER
    )


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_reopened_on_an_item_that_is_not_done_raises_value_error(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    with pytest.raises(ValueError, match="only done items can be reopened"):
        item.reopened(LATER)


def test_kept_as_true_keeps_a_done_item() -> None:
    # Setup
    item = an_item(stage=Stage.DONE)

    # Execute
    kept = item.kept_as(True, LATER)

    # Assert
    assert kept.kept is True


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_kept_as_true_on_an_item_that_is_not_done_raises_value_error(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    with pytest.raises(ValueError, match="only done items can be kept"):
        item.kept_as(True, LATER)


def test_kept_as_false_unkeeps_a_done_item() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, kept=True)

    # Execute
    unkept = item.kept_as(False, LATER)

    # Assert
    assert unkept.kept is False


def test_kept_as_false_unkeeps_a_reopened_item_that_stayed_kept() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, kept=True).reopened(LATER)

    # Execute
    unkept = item.kept_as(False, LATER)

    # Assert
    assert (unkept.stage, unkept.kept) == (Stage.WANT_TO, False)


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_kept_as_false_on_an_item_that_is_not_done_is_accepted(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    unkept = item.kept_as(False, LATER)

    # Assert
    assert unkept.kept is False


def test_kept_as_changes_nothing_but_kept_and_updated_at() -> None:
    # Setup
    item = an_item(stage=Stage.DONE, tags=("food",), parent_id="p1")

    # Execute
    kept = item.kept_as(True, LATER)

    # Assert
    assert kept == an_item(
        stage=Stage.DONE, kept=True, tags=("food",), parent_id="p1", updated_at=LATER
    )
