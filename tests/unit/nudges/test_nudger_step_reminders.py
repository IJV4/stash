from datetime import datetime, timedelta

import pytest
from builders import stored
from fakes.memory_store import MemoryStore
from fakes.vanishing_item_store import VanishingItemStore
from nudge_builders import (
    FOURTEEN_DAYS,
    SATURDAY,
    SATURDAY_MORNING,
    a_nudger,
    a_same_day_step,
    a_step_due_on,
    an_undated_date_night,
    only,
    stored_step,
    stored_step_due_on,
)
from planning_builders import DATE_NIGHT_ID

from stash.domain import Stage
from stash.nudges import StepReminder
from stash.store import Store


def step_reminders(store: Store, now: datetime) -> list[StepReminder]:
    return only(StepReminder, a_nudger(store).due(now))


def test_a_confirmed_open_step_is_due_at_the_reminder_time_on_its_due_date() -> None:
    # Setup
    store = MemoryStore()
    item = stored_step_due_on(store, SATURDAY)

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == [StepReminder(a_step_due_on(SATURDAY), item, SATURDAY_MORNING)]


def test_a_step_with_a_lead_time_is_due_that_many_days_before_the_item_date() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(stage=Stage.PLANNED, date=SATURDAY))
    stored_step(store, a_same_day_step(lead_days=1))

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert [reminder.due_at for reminder in due] == [SATURDAY_MORNING - timedelta(days=1)]


def test_a_step_that_is_not_confirmed_is_never_due() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(stage=Stage.DOING))
    stored_step(store, a_step_due_on(SATURDAY, confirmed=False))

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []


def test_a_step_that_is_done_is_never_due() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(stage=Stage.DOING))
    stored_step(store, a_step_due_on(SATURDAY, done=True))

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []


def test_a_step_whose_item_vanished_since_it_was_listed_is_never_due() -> None:
    # Setup
    store = VanishingItemStore()
    stored_step_due_on(store, SATURDAY)
    store.vanish_item_after_listing_open_steps(DATE_NIGHT_ID)

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []


@pytest.mark.parametrize("stage", [Stage.DONE, Stage.DROPPED])
def test_a_step_of_a_done_or_dropped_item_is_never_due(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored_step_due_on(store, SATURDAY, stage=stage)

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []


@pytest.mark.parametrize("stage", [Stage.INBOX, Stage.WANT_TO])
def test_a_step_of_an_item_that_is_not_planned_or_under_way_is_never_due(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored_step_due_on(store, SATURDAY, stage=stage)

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert due == []


@pytest.mark.parametrize("stage", [Stage.PLANNED, Stage.DOING])
def test_a_step_of_an_item_that_is_planned_or_under_way_is_due(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored_step_due_on(store, SATURDAY, stage=stage, date=SATURDAY)

    # Execute
    due = step_reminders(store, SATURDAY_MORNING)

    # Assert
    assert len(due) == 1


def test_a_step_with_a_lead_time_on_an_item_without_a_date_is_never_due() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(stage=Stage.DOING))
    stored_step(store, a_same_day_step(lead_days=3))

    # Execute
    due = step_reminders(store, SATURDAY_MORNING + FOURTEEN_DAYS)

    # Assert
    assert due == []
