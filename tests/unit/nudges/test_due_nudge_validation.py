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
from people_builders import a_key_date, a_person, a_person_date_reminder

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


def test_a_person_date_reminder_for_a_key_date_of_another_person_is_refused() -> None:
    # Setup
    strangers_key_date = a_key_date(person_id="someone-else")

    # Execute / Assert
    with pytest.raises(ValueError, match="belongs to"):
        a_person_date_reminder(person=a_person(), key_date=strangers_key_date)


def test_a_person_date_reminder_with_a_negative_lead_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="lead"):
        a_person_date_reminder(lead=-1)


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
