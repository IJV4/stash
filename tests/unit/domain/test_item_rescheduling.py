from datetime import date, datetime
from typing import Any

import pytest
from builders import BASE, LATER, NAIVE, PLANNED_FOR, an_item, an_item_at

from stash.domain import Stage

NEW_DATE = date(2026, 12, 25)
A_DATETIME: Any = datetime(2026, 12, 25, 9, 0)

RESCHEDULE_TABLE = [
    pytest.param(Stage.INBOX, NEW_DATE, Stage.INBOX, NEW_DATE, id="inbox-dated"),
    pytest.param(Stage.INBOX, None, Stage.INBOX, None, id="inbox-undated"),
    pytest.param(Stage.WANT_TO, NEW_DATE, Stage.WANT_TO, NEW_DATE, id="want_to-dated"),
    pytest.param(Stage.WANT_TO, None, Stage.WANT_TO, None, id="want_to-undated"),
    pytest.param(Stage.PLANNED, NEW_DATE, Stage.PLANNED, NEW_DATE, id="planned-dated"),
    pytest.param(Stage.PLANNED, None, Stage.WANT_TO, None, id="planned-undated"),
    pytest.param(Stage.DOING, NEW_DATE, Stage.DOING, NEW_DATE, id="doing-dated"),
    pytest.param(Stage.DOING, None, Stage.DOING, None, id="doing-undated"),
    pytest.param(Stage.DONE, NEW_DATE, Stage.DONE, NEW_DATE, id="done-dated"),
    pytest.param(Stage.DONE, None, Stage.DONE, None, id="done-undated"),
    pytest.param(Stage.DROPPED, NEW_DATE, Stage.DROPPED, NEW_DATE, id="dropped-dated"),
    pytest.param(Stage.DROPPED, None, Stage.DROPPED, None, id="dropped-undated"),
]


@pytest.mark.parametrize(("stage", "new_date", "expected_stage", "expected_date"), RESCHEDULE_TABLE)
def test_rescheduling_gives_the_expected_stage_and_date(
    stage: Stage, new_date: date | None, expected_stage: Stage, expected_date: date | None
) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    rescheduled = item.rescheduled(new_date, LATER)

    # Assert
    assert (rescheduled.stage, rescheduled.date) == (expected_stage, expected_date)


@pytest.mark.parametrize("stage", list(Stage))
def test_rescheduling_bumps_updated_at_in_every_stage(stage: Stage) -> None:
    # Setup
    item = an_item_at(stage)

    # Execute
    rescheduled = item.rescheduled(NEW_DATE, LATER)

    # Assert
    assert rescheduled.updated_at == LATER


def test_rescheduling_a_planned_item_to_no_date_bumps_updated_at() -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    rescheduled = item.rescheduled(None, LATER)

    # Assert
    assert rescheduled.updated_at == LATER


def test_rescheduling_a_dropped_item_keeps_its_drop_reason() -> None:
    # Setup
    item = an_item_at(Stage.DROPPED, drop_reason="Not for me")

    # Execute
    rescheduled = item.rescheduled(NEW_DATE, LATER)

    # Assert
    assert rescheduled.drop_reason == "Not for me"


def test_clearing_the_date_of_a_dropped_item_keeps_its_drop_reason() -> None:
    # Setup
    item = an_item(stage=Stage.DROPPED, drop_reason="Not for me", date=PLANNED_FOR)

    # Execute
    rescheduled = item.rescheduled(None, LATER)

    # Assert
    assert rescheduled.drop_reason == "Not for me"


def test_rescheduling_changes_nothing_but_the_date_and_updated_at() -> None:
    # Setup
    item = an_item(stage=Stage.DOING, date=PLANNED_FOR, tags=("ramen",), kept=True)

    # Execute
    rescheduled = item.rescheduled(NEW_DATE, LATER)

    # Assert
    assert rescheduled == an_item(
        stage=Stage.DOING, date=NEW_DATE, tags=("ramen",), kept=True, updated_at=LATER
    )


def test_rescheduling_keeps_the_cool_off_date() -> None:
    # Setup
    item = an_item(date=PLANNED_FOR, cool_off_until=NEW_DATE)

    # Execute
    rescheduled = item.rescheduled(None, LATER)

    # Assert
    assert rescheduled.cool_off_until == NEW_DATE


def test_rescheduling_leaves_the_original_item_unchanged() -> None:
    # Setup
    item = an_item_at(Stage.PLANNED)

    # Execute
    item.rescheduled(None, LATER)

    # Assert
    assert (item.stage, item.date, item.updated_at) == (Stage.PLANNED, PLANNED_FOR, BASE)


def test_rescheduling_to_a_datetime_is_refused() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="date must be a date, not a datetime"):
        item.rescheduled(A_DATETIME, LATER)


def test_rescheduling_with_a_naive_now_is_refused() -> None:
    # Setup
    item = an_item()

    # Execute / Assert
    with pytest.raises(ValueError, match="updated_at must be timezone-aware"):
        item.rescheduled(NEW_DATE, NAIVE)
