from datetime import datetime

from builders import stored
from fakes.store_factories import FreshStore
from nudge_builders import (
    FOURTEEN_DAYS,
    SATURDAY_MORNING,
    a_nudger,
    a_same_day_step,
    an_undated_date_night,
    only,
    stored_step,
)

from stash.domain import Stage
from stash.nudges import StepReminder
from stash.store import Store


def step_reminders(store: Store, now: datetime) -> list[StepReminder]:
    return only(StepReminder, a_nudger(store).due(now))


def test_a_step_with_a_lead_time_on_an_item_without_a_date_is_never_due() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_undated_date_night(stage=Stage.DOING))
    stored_step(store, a_same_day_step(lead_days=3))

    # Execute
    due = step_reminders(store, SATURDAY_MORNING + FOURTEEN_DAYS)

    # Assert
    assert due == []
