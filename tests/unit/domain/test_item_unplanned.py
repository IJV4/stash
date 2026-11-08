import pytest
from builders import LATER, NOT_PLANNED_STAGES, PLANNED_FOR, an_item, an_item_at

from stash.domain import Stage


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_unplanning_an_item_that_is_not_planned_returns_the_same_item(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned is item


def test_unplanning_a_dated_want_to_item_keeps_its_date() -> None:
    # Setup
    item = an_item(stage=Stage.WANT_TO, date=PLANNED_FOR)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned.date == PLANNED_FOR
