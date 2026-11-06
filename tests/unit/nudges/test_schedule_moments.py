from datetime import UTC, date, datetime, time, timedelta

from builders import MICROSECOND, in_los_angeles
from nudge_builders import SATURDAY, SUNDAY, a_nudge_schedule

FOLLOW_UP_SLOT = in_los_angeles(SUNDAY, 9)


def test_a_reminder_is_due_at_the_reminder_time_on_the_day() -> None:
    # Execute
    instant = a_nudge_schedule(reminder_time=time(7, 30)).reminder_at(SATURDAY)

    # Assert
    assert instant == in_los_angeles(SATURDAY, 7, 30)


def test_a_follow_up_is_due_at_the_follow_up_time_the_day_after_the_item_date() -> None:
    # Execute
    instant = a_nudge_schedule(followup_time=time(18, 15)).followup_at(SATURDAY)

    # Assert
    assert instant == in_los_angeles(SUNDAY, 18, 15)


def test_a_follow_up_for_the_last_day_of_a_month_is_due_on_the_first_of_the_next() -> None:
    # Execute
    instant = a_nudge_schedule().followup_at(date(2027, 2, 28))

    # Assert
    assert instant == in_los_angeles(date(2027, 3, 1), 9)


def test_before_todays_follow_up_time_the_latest_follow_up_slot_is_yesterdays() -> None:
    # Execute
    slot = a_nudge_schedule().latest_followup_slot(FOLLOW_UP_SLOT - MICROSECOND)

    # Assert
    assert slot == in_los_angeles(SATURDAY, 9)


def test_exactly_at_todays_follow_up_time_the_latest_follow_up_slot_is_todays() -> None:
    # Execute
    slot = a_nudge_schedule().latest_followup_slot(FOLLOW_UP_SLOT)

    # Assert
    assert slot == FOLLOW_UP_SLOT


def test_after_todays_follow_up_time_the_latest_follow_up_slot_is_todays() -> None:
    # Execute
    slot = a_nudge_schedule().latest_followup_slot(FOLLOW_UP_SLOT + timedelta(hours=5))

    # Assert
    assert slot == FOLLOW_UP_SLOT


def test_the_stuck_cutoff_is_the_configured_number_of_days_before_the_instant() -> None:
    # Execute
    cutoff = a_nudge_schedule(stuck_doing_days=7).stuck_cutoff(FOLLOW_UP_SLOT)

    # Assert
    assert cutoff == in_los_angeles(date(2027, 2, 7), 9)


def test_the_local_date_of_an_instant_late_on_a_saturday_evening_is_saturday() -> None:
    # Execute
    day = a_nudge_schedule().local_date(datetime(2027, 2, 14, 3, 0, tzinfo=UTC))

    # Assert
    assert day == SATURDAY


def test_follow_ups_due_between_two_dates_belong_to_items_dated_the_day_before_each() -> None:
    # Execute
    item_dates = a_nudge_schedule().item_dates_followed_up_between(SUNDAY, date(2027, 2, 16))

    # Assert
    assert item_dates == (SATURDAY, date(2027, 2, 15))


def test_follow_ups_due_on_the_first_of_a_month_belong_to_items_dated_the_month_before() -> None:
    # Setup
    item_dates = a_nudge_schedule().item_dates_followed_up_between(
        date(2027, 3, 1), date(2027, 3, 1)
    )

    # Assert
    assert item_dates == (date(2027, 2, 28), date(2027, 2, 28))
