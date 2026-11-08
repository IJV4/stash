from datetime import datetime, timedelta

import pytest
from builders import MICROSECOND, NAIVE
from fakes.store_factories import FreshStore
from nudge_builders import (
    FOURTEEN_DAYS,
    SATURDAY_MORNING,
    SUNDAY,
    SUNDAY_MORNING,
    a_nudger,
    only,
    stored_date_night_with_its_step,
)

from stash.domain import Item
from stash.nudges import DateReminder, FollowUp, StepReminder

A_DAY = timedelta(days=1)

EACH_KIND = [
    pytest.param(StepReminder, SATURDAY_MORNING, id="step reminder"),
    pytest.param(DateReminder, SATURDAY_MORNING, id="date reminder"),
    pytest.param(FollowUp, SUNDAY_MORNING, id="follow-up"),
]


def a_store_where_every_kind_comes_due() -> tuple[FreshStore, Item]:
    store = FreshStore()
    return store, stored_date_night_with_its_step(store)


def due_of_kind(kind: type, store: FreshStore, now: datetime) -> list:
    return only(kind, a_nudger(store).due(now))


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_a_nudge_is_not_due_a_microsecond_before_its_time(kind: type, due_at: datetime) -> None:
    # Setup
    store, _ = a_store_where_every_kind_comes_due()

    # Execute
    due = due_of_kind(kind, store, due_at - MICROSECOND)

    # Assert
    assert due == []


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_a_nudge_is_still_due_a_day_after_its_time(kind: type, due_at: datetime) -> None:
    # Setup
    store, _ = a_store_where_every_kind_comes_due()

    # Execute
    due = due_of_kind(kind, store, due_at + A_DAY)

    # Assert
    assert len(due) == 1


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_a_nudge_is_still_due_exactly_fourteen_days_after_its_time(
    kind: type, due_at: datetime
) -> None:
    # Setup
    store, _ = a_store_where_every_kind_comes_due()

    # Execute
    due = due_of_kind(kind, store, due_at + FOURTEEN_DAYS)

    # Assert
    assert len(due) == 1


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_a_nudge_is_dropped_silently_once_more_than_fourteen_days_old(
    kind: type, due_at: datetime
) -> None:
    # Setup
    store, _ = a_store_where_every_kind_comes_due()

    # Execute
    due = due_of_kind(kind, store, due_at + FOURTEEN_DAYS + MICROSECOND)

    # Assert
    assert due == []


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_a_nudge_that_was_already_sent_is_not_due_again(kind: type, due_at: datetime) -> None:
    # Setup
    store, _ = a_store_where_every_kind_comes_due()
    [reminder] = due_of_kind(kind, store, due_at)
    store.record_all_sent([reminder.nudge], due_at)

    # Execute
    due = due_of_kind(kind, store, due_at)

    # Assert
    assert due == []


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_dropping_the_item_after_one_check_removes_the_nudge_from_the_next(
    kind: type, due_at: datetime
) -> None:
    # Setup
    store, item = a_store_where_every_kind_comes_due()
    nudger = a_nudger(store)
    nudger.due(due_at)
    store.save_item(item.dropped(None, due_at))

    # Execute
    due = only(kind, nudger.due(due_at))

    # Assert
    assert due == []


@pytest.mark.parametrize(("kind", "due_at"), EACH_KIND)
def test_moving_the_item_date_a_day_later_moves_the_nudge_a_day_later(
    kind: type, due_at: datetime
) -> None:
    # Setup
    store, item = a_store_where_every_kind_comes_due()
    nudger = a_nudger(store)
    nudger.due(due_at)
    store.save_item(item.rescheduled(SUNDAY, due_at))

    # Execute
    due = only(kind, nudger.due(due_at + A_DAY))

    # Assert
    assert [reminder.due_at for reminder in due] == [due_at + A_DAY]


def test_asking_what_is_due_at_a_time_without_a_time_zone_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="now"):
        a_nudger(FreshStore()).due(NAIVE)
