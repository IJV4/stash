from datetime import UTC, datetime, timedelta

from builders import FALL_BACK_DAY, SPRING_FORWARD_DAY, fetched_item, in_los_angeles, stored
from capture_rig import a_fix_handler
from fakes.failing_nudge_sender import FailingNudgeSender
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle
from nudge_builders import (
    BOOK_THE_TABLE_LINE,
    DATE_NIGHT_LINE,
    DIGEST_LINE,
    FOLLOW_UP_LINE,
    FRIDAY,
    MONDAY,
    SATURDAY,
    SATURDAY_MORNING,
    STUCK_BOOK_LINE,
    SUNDAY,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    SUNDAY_NOON,
    a_planned_date_night,
    a_step_due_on,
    stored_date_night_week,
    stored_date_night_with_its_step,
    stored_step,
    stored_step_due_on,
)
from nudge_rig import MINUTE, a_nudge_rig, hourly_ticks_with_minutes_around, ticks_between
from planning_builders import DATE_NIGHT_ID

from stash.capture.callbacks import FixAction, FixKind, date_argument
from stash.domain import Stage

CATCH_UP_TEXT = "\n".join(
    [
        "While I was offline:",
        BOOK_THE_TABLE_LINE,
        DATE_NIGHT_LINE,
        FOLLOW_UP_LINE,
        DIGEST_LINE,
        STUCK_BOOK_LINE,
    ]
)


def test_ticking_through_the_week_sends_the_reminders_the_follow_up_and_the_digest_once_each() -> (
    None
):
    # Setup
    store = FreshStore()
    stored_date_night_week(store)
    rig = a_nudge_rig(store)
    week = hourly_ticks_with_minutes_around(
        in_los_angeles(FRIDAY),
        in_los_angeles(MONDAY),
        (SATURDAY_MORNING, SUNDAY_MORNING, SUNDAY_DIGEST_TIME),
    )
    rig.digests_before_were_sent(week[0])

    # Execute
    rig.tick_through(week)

    # Assert
    assert rig.sent_texts() == [
        (SATURDAY_MORNING, f"{BOOK_THE_TABLE_LINE}\n{DATE_NIGHT_LINE}"),
        (SUNDAY_MORNING, FOLLOW_UP_LINE),
        (SUNDAY_DIGEST_TIME, f"{DIGEST_LINE}\n{STUCK_BOOK_LINE}"),
    ]


def test_with_the_pc_off_from_friday_evening_to_sunday_noon_one_catch_up_message_is_sent_once() -> (
    None
):
    # Setup
    store = FreshStore()
    stored_date_night_week(store)
    rig = a_nudge_rig(store)
    friday_evening = in_los_angeles(FRIDAY, 18)
    rig.digests_before_were_sent(friday_evening)
    rig.tick(friday_evening)

    # Execute
    rig.tick_through([SUNDAY_NOON, SUNDAY_NOON + MINUTE])

    # Assert
    assert rig.sent_texts() == [(SUNDAY_NOON, CATCH_UP_TEXT)]


def test_the_reminder_on_the_day_the_clocks_go_forward_fires_once_at_sixteen_hundred_utc() -> None:
    # Setup
    store = FreshStore()
    stored_step_due_on(store, SPRING_FORWARD_DAY)
    rig = a_nudge_rig(store)
    fires_at = datetime(2027, 3, 14, 16, 0, tzinfo=UTC)
    ticks = hourly_ticks_with_minutes_around(fires_at.replace(hour=0), fires_at, (fires_at,))
    rig.digests_before_were_sent(ticks[0])

    # Execute
    rig.tick_through(ticks)

    # Assert
    assert rig.sent_texts() == [(fires_at, "⏰ Book the table — for Date night")]


def test_the_reminder_on_the_day_the_clocks_go_back_fires_once_at_seventeen_hundred_utc() -> None:
    # Setup
    store = FreshStore()
    stored_step_due_on(store, FALL_BACK_DAY)
    rig = a_nudge_rig(store)
    fires_at = datetime(2027, 11, 7, 17, 0, tzinfo=UTC)
    ticks = hourly_ticks_with_minutes_around(fires_at.replace(hour=0), fires_at, (fires_at,))
    rig.digests_before_were_sent(ticks[0])

    # Execute
    rig.tick_through(ticks)

    # Assert
    assert rig.sent_texts() == [(fires_at, "⏰ Book the table — for Date night")]


def test_dropping_the_item_before_saturday_morning_sends_no_step_or_date_reminder() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)
    friday_evening = in_los_angeles(FRIDAY, 20)
    rig.digests_before_were_sent(friday_evening)
    a_lifecycle(store).drop(DATE_NIGHT_ID, None)

    # Execute
    rig.tick_through(
        hourly_ticks_with_minutes_around(
            friday_evening, in_los_angeles(SATURDAY, 12), (SATURDAY_MORNING,)
        )
    )

    # Assert
    assert rig.sent_texts() == []


def test_a_date_moved_in_the_store_before_saturday_morning_moves_the_step_reminder_with_it() -> (
    None
):
    # Setup
    store = FreshStore()
    date_night = stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)
    friday_evening = in_los_angeles(FRIDAY, 20)
    rig.digests_before_were_sent(friday_evening)
    store.save_item(date_night.rescheduled(SUNDAY, friday_evening))

    # Execute
    rig.tick_through(
        hourly_ticks_with_minutes_around(
            friday_evening, in_los_angeles(SUNDAY, 11), (SATURDAY_MORNING, SUNDAY_MORNING)
        )
    )

    # Assert
    assert [
        (at, line)
        for at, text in rig.sent_texts()
        for line in text.splitlines()
        if line.startswith("⏰")
    ] == [(SUNDAY_MORNING, "⏰ Book the table — for Date night (Sun Feb 14)")]


def test_rescheduling_moves_the_reminders_and_the_follow_up_to_the_new_date() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)
    friday_evening = in_los_angeles(FRIDAY, 20)
    rig.digests_before_were_sent(friday_evening)
    a_lifecycle(store, clock=lambda: friday_evening).reschedule(DATE_NIGHT_ID, SUNDAY)
    monday_morning = in_los_angeles(MONDAY, 9)

    # Execute
    rig.tick_through(
        hourly_ticks_with_minutes_around(
            friday_evening,
            in_los_angeles(MONDAY, 12),
            (SATURDAY_MORNING, SUNDAY_MORNING, monday_morning),
        )
    )

    # Assert
    assert [
        (at, line)
        for at, text in rig.sent_texts()
        for line in text.splitlines()
        if line.startswith("⏰") or line == FOLLOW_UP_LINE
    ] == [
        (SUNDAY_MORNING, "⏰ Book the table — for Date night (Sun Feb 14)"),
        (monday_morning, FOLLOW_UP_LINE),
    ]


def test_a_failed_send_leaves_the_message_unmarked_and_the_next_tick_sends_it_once() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store, send=FailingNudgeSender(failures=1))
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    rig.tick_through(ticks_between(SATURDAY_MORNING, SATURDAY_MORNING + 3 * MINUTE, MINUTE))

    # Assert
    assert rig.sent_texts() == [
        (SATURDAY_MORNING + MINUTE, f"{BOOK_THE_TABLE_LINE}\n{DATE_NIGHT_LINE}")
    ]


def test_pressing_didnt_happen_moves_the_date_night_back_to_want_to_with_no_date() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SATURDAY_MORNING)
    rig.tick_through([SATURDAY_MORNING, SUNDAY_MORNING])
    [[_, didnt_happen]] = rig.sent[-1][1].buttons

    # Execute
    a_fix_handler(store).apply(didnt_happen.data)

    # Assert
    item = fetched_item(store, DATE_NIGHT_ID)
    assert (item.stage, item.date) == (Stage.WANT_TO, None)


def test_pressing_didnt_happen_after_the_item_was_rescheduled_leaves_it_as_it_is() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SATURDAY_MORNING)
    rig.tick_through([SATURDAY_MORNING, SUNDAY_MORNING])
    [[_, didnt_happen]] = rig.sent[-1][1].buttons
    rescheduled = a_lifecycle(store).reschedule(DATE_NIGHT_ID, SATURDAY + timedelta(days=7))

    # Execute
    a_fix_handler(store).apply(didnt_happen.data)

    # Assert
    assert fetched_item(store, DATE_NIGHT_ID) == rescheduled


def test_a_step_due_tomorrow_sends_no_reminder_once_didnt_happen_moved_the_item_to_want_to() -> (
    None
):
    # Setup
    store = FreshStore()
    stored(store, a_planned_date_night())
    stored_step(store, a_step_due_on(SUNDAY))
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SUNDAY_MORNING)
    didnt_happen = FixAction(FixKind.NOT_HAPPENED, DATE_NIGHT_ID, date_argument(SATURDAY))
    a_fix_handler(store).apply(didnt_happen.encode())

    # Execute
    rig.tick(SUNDAY_MORNING)

    # Assert
    assert rig.sent_texts() == []
