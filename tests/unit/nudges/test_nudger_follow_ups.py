from datetime import datetime

import pytest
from builders import NOT_PLANNED_STAGES, an_outcome, stored
from fakes.memory_store import MemoryStore
from nudge_builders import (
    SUNDAY_MORNING,
    a_nudger,
    a_planned_date_night,
    a_store_with_a_pending_follow_up,
    only,
)
from planning_builders import DATE_NIGHT_ID

from stash.domain import Stage
from stash.nudges import FollowUp
from stash.store import Store


def follow_ups(store: Store, now: datetime) -> list[FollowUp]:
    return only(FollowUp, a_nudger(store).due(now))


def test_a_planned_item_without_an_outcome_is_followed_up_the_morning_after_its_date() -> None:
    # Setup
    store = MemoryStore()
    date_night = stored(store, a_planned_date_night())

    # Execute
    due = follow_ups(store, SUNDAY_MORNING)

    # Assert
    assert due == [FollowUp(date_night, SUNDAY_MORNING)]


def test_a_planned_item_with_an_outcome_is_not_followed_up() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.add_outcome(an_outcome(item_id=DATE_NIGHT_ID))

    # Execute
    due = follow_ups(store, SUNDAY_MORNING)

    # Assert
    assert due == []


@pytest.mark.parametrize("stage", NOT_PLANNED_STAGES)
def test_an_item_that_is_not_planned_is_not_followed_up(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(stage=stage))

    # Execute
    due = follow_ups(store, SUNDAY_MORNING)

    # Assert
    assert due == []
