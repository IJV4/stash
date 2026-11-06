import pytest
from builders import LATER, NOT_PLANNED_STAGES, PLANNED_FOR, an_item, an_item_at

from stash.domain import Stage


def test_unplanning_a_planned_item_puts_it_back_to_want_to() -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned.stage is Stage.WANT_TO


def test_unplanning_a_planned_item_clears_its_date() -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned.date is None


def test_unplanning_a_planned_item_bumps_updated_at() -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned.updated_at == LATER


def test_unplanning_a_planned_item_changes_nothing_else() -> None:
    # Setup
    item = an_item(stage=Stage.PLANNED, date=PLANNED_FOR, tags=("ramen",), kept=True)

    # Execute
    unplanned = item.unplanned(LATER)

    # Assert
    assert unplanned == an_item(stage=Stage.WANT_TO, tags=("ramen",), kept=True, updated_at=LATER)


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
