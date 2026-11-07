from datetime import datetime, timedelta

import pytest
from builders import MICROSECOND, stored
from nudge_builders import (
    FOURTEEN_DAYS,
    FRIDAY,
    SATURDAY_MORNING,
    SUNDAY_MORNING,
    SUNDAY_NOON,
    a_date_reminder,
    a_follow_up_sent_for_another_item,
    a_nudger,
    a_planned_date_night,
    a_store_with_a_pending_follow_up,
    a_weekly_digest,
    only,
)
from planning_builders import DATE_NIGHT_ID

from stash.nudges import DateReminder, FollowUp, WeeklyDigest
from stash.store import Store


def follow_ups(store: Store, now: datetime) -> list[FollowUp]:
    return only(FollowUp, a_nudger(store).due(now))


def test_several_days_of_follow_ups_are_due_together_when_no_follow_up_was_sent_for_a_while() -> (
    None
):
    # Setup
    store = a_store_with_a_pending_follow_up()
    friday_dinner = stored(store, a_planned_date_night(id="friday-dinner", date=FRIDAY))

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert [follow_up.item.id for follow_up in due] == [friday_dinner.id, DATE_NIGHT_ID]


def test_with_no_follow_up_ever_sent_a_follow_up_is_due() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert len(due) == 1


def test_a_follow_up_sent_before_todays_follow_up_time_does_not_hold_back_todays() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent([a_follow_up_sent_for_another_item()], SATURDAY_MORNING)

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert len(due) == 1


@pytest.mark.parametrize("other", [a_date_reminder(), a_weekly_digest()], ids=["date", "digest"])
def test_a_nudge_that_is_not_a_follow_up_sent_after_the_follow_up_time_holds_nothing_back(
    other: DateReminder | WeeklyDigest,
) -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent([other.nudge], SUNDAY_MORNING + timedelta(minutes=30))

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert len(due) == 1


def test_a_follow_up_sent_a_microsecond_before_todays_slot_does_not_hold_back_todays() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent([a_follow_up_sent_for_another_item()], SUNDAY_MORNING - MICROSECOND)

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert len(due) == 1


def test_a_follow_up_sent_exactly_at_todays_follow_up_time_holds_back_the_others() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent([a_follow_up_sent_for_another_item()], SUNDAY_MORNING)

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert due == []


def test_a_follow_up_sent_after_todays_follow_up_time_holds_back_the_others() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent(
        [a_follow_up_sent_for_another_item()], SUNDAY_MORNING + timedelta(minutes=30)
    )

    # Execute
    due = follow_ups(store, SUNDAY_NOON)

    # Assert
    assert due == []


def test_a_held_back_follow_up_waits_until_just_before_the_next_follow_up_time() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent(
        [a_follow_up_sent_for_another_item()], SUNDAY_MORNING + timedelta(minutes=30)
    )
    next_slot = SUNDAY_MORNING + timedelta(days=1)

    # Execute
    due = follow_ups(store, next_slot - MICROSECOND)

    # Assert
    assert due == []


def test_a_held_back_follow_up_is_sent_at_the_next_follow_up_time() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent(
        [a_follow_up_sent_for_another_item()], SUNDAY_MORNING + timedelta(minutes=30)
    )
    next_slot = SUNDAY_MORNING + timedelta(days=1)

    # Execute
    due = follow_ups(store, next_slot)

    # Assert
    assert [follow_up.due_at for follow_up in due] == [SUNDAY_MORNING]


def test_a_follow_up_held_back_by_every_slot_is_dropped_once_the_window_passes_it() -> None:
    # Setup
    store = a_store_with_a_pending_follow_up()
    store.record_all_sent(
        [a_follow_up_sent_for_another_item()], SUNDAY_MORNING + timedelta(minutes=30)
    )

    # Execute
    due = follow_ups(store, SUNDAY_MORNING + FOURTEEN_DAYS + MICROSECOND)

    # Assert
    assert due == []
