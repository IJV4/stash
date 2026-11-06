from datetime import timedelta

import pytest
from builders import stored
from fakes.ledger_recording_store import LedgerCrashed, LedgerRecordingStore
from fakes.memory_store import MemoryStore
from nudge_builders import (
    FRIDAY,
    SATURDAY_MORNING,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    SUNDAY_NOON,
    a_follow_up,
    a_nudger,
    a_planned_date_night,
    a_step_reminder,
    a_weekly_digest,
    only,
    stored_date_night_week,
    stored_date_night_with_its_step,
)
from planning_builders import DATE_NIGHT_ID

from stash.domain import NudgeKind
from stash.nudges import DateReminder, FollowUp, NudgeMessage, StepReminder, WeeklyDigest


def test_marking_a_message_sent_for_the_first_time_reports_that_all_of_it_was_recorded() -> None:
    # Setup
    nudger = a_nudger(MemoryStore())

    # Execute
    recorded_all = nudger.mark_sent(NudgeMessage((a_step_reminder(),), catch_up=False), SUNDAY_NOON)

    # Assert
    assert recorded_all is True


def test_marking_a_message_sent_when_another_sender_recorded_one_of_its_nudges_reports_false() -> (
    None
):
    # Setup
    store = MemoryStore()
    nudger = a_nudger(store)
    store.record_sent(a_follow_up().nudge, SUNDAY_MORNING)
    message = NudgeMessage((a_follow_up(), a_step_reminder()), catch_up=True)

    # Execute
    recorded_all = nudger.mark_sent(message, SUNDAY_NOON)

    # Assert
    assert recorded_all is False


def test_marking_a_message_sent_still_records_the_other_nudges_when_one_was_already_recorded() -> (
    None
):
    # Setup
    store = MemoryStore()
    nudger = a_nudger(store)
    store.record_sent(a_follow_up().nudge, SUNDAY_MORNING)
    message = NudgeMessage((a_follow_up(), a_step_reminder()), catch_up=True)

    # Execute
    nudger.mark_sent(message, SUNDAY_NOON)

    # Assert
    assert store.was_sent(a_step_reminder().nudge.key)


def test_a_marked_message_is_not_due_again() -> None:
    # Setup
    store = MemoryStore()
    stored_date_night_week(store)
    nudger = a_nudger(store)
    for due in nudger.due(SUNDAY_NOON):
        nudger.mark_sent(NudgeMessage((due,), catch_up=False), SUNDAY_NOON)

    # Execute
    due = nudger.due(SUNDAY_NOON)

    # Assert
    assert due == []


def test_marking_records_the_time_the_message_was_sent() -> None:
    # Setup
    store = MemoryStore()
    nudger = a_nudger(store)

    # Execute
    nudger.mark_sent(NudgeMessage((a_follow_up(),), catch_up=False), SUNDAY_NOON)

    # Assert
    assert store.last_sent(NudgeKind.FOLLOWUP) == SUNDAY_NOON


def test_a_digest_is_recorded_after_the_stuck_items_that_rode_it() -> None:
    # Setup
    store = LedgerRecordingStore()
    nudger = a_nudger(store)
    message = NudgeMessage((a_weekly_digest(),), catch_up=False)

    # Execute
    nudger.mark_sent(message, SUNDAY_DIGEST_TIME)

    # Assert
    assert store.recorded == [NudgeKind.STUCK, NudgeKind.DIGEST]


def test_a_crash_before_the_digest_is_recorded_repeats_the_digest_without_the_recorded_items() -> (
    None
):
    # Setup
    store = LedgerRecordingStore()
    nudger = a_nudger(store)
    stored_date_night_week(store)
    [*_, digest] = nudger.due(SUNDAY_NOON)
    store.crash_on = NudgeKind.DIGEST
    with pytest.raises(LedgerCrashed):
        nudger.mark_sent(NudgeMessage((digest,), catch_up=False), SUNDAY_NOON)
    store.crash_on = None

    # Execute
    due = nudger.due(SUNDAY_NOON)

    # Assert
    assert WeeklyDigest(SUNDAY_DIGEST_TIME, ()) in due


def test_a_crash_after_the_first_reminder_of_a_message_is_recorded_leaves_only_the_rest_due() -> (
    None
):
    # Setup
    store = LedgerRecordingStore()
    stored_date_night_with_its_step(store)
    nudger = a_nudger(store)
    reminders = tuple(
        due for due in nudger.due(SATURDAY_MORNING) if isinstance(due, StepReminder | DateReminder)
    )
    store.crash_after = 1
    with pytest.raises(LedgerCrashed):
        nudger.mark_sent(NudgeMessage(reminders, catch_up=False), SATURDAY_MORNING)
    store.crash_after = None

    # Execute
    due = nudger.due(SATURDAY_MORNING)

    # Assert
    assert [nudge.nudge.kind for nudge in due if not isinstance(nudge, WeeklyDigest)] == [
        NudgeKind.ITEM_DATE
    ]


def a_store_whose_ledger_crashes_after_the_first_of_two_follow_ups() -> LedgerRecordingStore:
    store = LedgerRecordingStore()
    stored_date_night_with_its_step(store)
    stored(store, a_planned_date_night(id="friday-dinner", date=FRIDAY))
    nudger = a_nudger(store)
    follow_ups = tuple(due for due in nudger.due(SUNDAY_NOON) if isinstance(due, FollowUp))
    store.crash_after = 1
    with pytest.raises(LedgerCrashed):
        nudger.mark_sent(NudgeMessage(follow_ups, catch_up=False), SUNDAY_NOON)
    store.crash_after = None
    return store


def test_a_crash_after_the_first_of_two_follow_ups_holds_the_other_until_the_next_slot() -> None:
    # Setup
    store = a_store_whose_ledger_crashes_after_the_first_of_two_follow_ups()

    # Execute
    due = a_nudger(store).due(SUNDAY_NOON)

    # Assert
    assert only(FollowUp, due) == []


def test_a_follow_up_held_back_by_a_crash_is_due_at_the_next_slot_and_not_lost() -> None:
    # Setup
    store = a_store_whose_ledger_crashes_after_the_first_of_two_follow_ups()

    # Execute
    due = a_nudger(store).due(SUNDAY_MORNING + timedelta(days=1))

    # Assert
    assert [follow_up.item.id for follow_up in only(FollowUp, due)] == [DATE_NIGHT_ID]
