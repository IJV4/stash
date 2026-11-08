import pytest
from builders import (
    LATER,
    NON_DONE_STAGES,
    an_item,
    an_item_at,
)

from stash.domain.item import Stage


def test_completed_on_a_done_item_raises_value_error() -> None:
    # Setup
    item = an_item(stage=Stage.DONE)

    # Execute / Assert
    with pytest.raises(ValueError, match="already done"):
        item.completed(LATER)


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_reopened_on_an_item_that_is_not_done_raises_value_error(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    with pytest.raises(ValueError, match="only done items can be reopened"):
        item.reopened(LATER)


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_kept_as_true_on_an_item_that_is_not_done_raises_value_error(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute / Assert
    with pytest.raises(ValueError, match="only done items can be kept"):
        item.kept_as(True, LATER)
