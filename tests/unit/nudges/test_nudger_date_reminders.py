from datetime import datetime

import pytest
from builders import NOT_PLANNED_STAGES, stored
from fakes.store_factories import FreshStore
from nudge_builders import (
    SATURDAY,
    SATURDAY_MORNING,
    a_nudger,
    a_planned_date_night,
    only,
)

from stash.domain import Stage
from stash.nudges import DateReminder
from stash.store import Store


def date_reminders(store: Store, now: datetime) -> list[DateReminder]:
    return only(DateReminder, a_nudger(store).due(now))


def test_a_planned_item_is_due_at_the_reminder_time_on_its_date() -> None:
    # Setup
    store = FreshStore()
    date_night = stored(store, a_planned_date_night())

    # Execute
    due = date_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == [DateReminder(date_night, SATURDAY, SATURDAY_MORNING)]


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_never_gets_a_date_reminder(stage: Stage) -> None:
    # Setup
    store = FreshStore()
    stored(store, a_planned_date_night(stage=stage))

    # Execute
    due = date_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []
