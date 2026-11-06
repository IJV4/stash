from collections.abc import Callable

import pytest
from builders import NAIVE, an_item
from nudge_builders import (
    SATURDAY,
    SATURDAY_MORNING,
    SUNDAY,
    SUNDAY_DIGEST_TIME,
    a_planned_date_night,
    a_same_day_step,
    a_stuck_book,
)

from stash.nudges import DateReminder, FollowUp, StepReminder, StuckItem, WeeklyDigest


def test_a_step_reminder_for_an_item_the_step_does_not_belong_to_is_refused() -> None:
    # Setup
    other_item = an_item(id="other", title="Other")

    # Execute / Assert
    with pytest.raises(ValueError, match="belongs to"):
        StepReminder(a_same_day_step(), other_item, SATURDAY_MORNING)


def test_a_date_reminder_for_a_day_that_is_not_the_item_date_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item date"):
        DateReminder(a_planned_date_night(), SUNDAY, SATURDAY_MORNING)


def test_a_digest_holding_a_stuck_item_from_another_instant_is_refused() -> None:
    # Setup
    stuck = StuckItem(a_stuck_book(), SATURDAY_MORNING)

    # Execute / Assert
    with pytest.raises(ValueError, match="same instant"):
        WeeklyDigest(SUNDAY_DIGEST_TIME, (stuck,))


@pytest.mark.parametrize(
    "build",
    [
        lambda: StepReminder(a_same_day_step(), a_planned_date_night(), NAIVE),
        lambda: DateReminder(a_planned_date_night(), SATURDAY, NAIVE),
        lambda: FollowUp(a_planned_date_night(), NAIVE),
        lambda: StuckItem(a_stuck_book(), NAIVE),
        lambda: WeeklyDigest(NAIVE, ()),
    ],
    ids=["step", "date", "follow-up", "stuck", "digest"],
)
def test_a_due_nudge_without_a_time_zone_is_refused(build: Callable[[], object]) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="due_at"):
        build()
