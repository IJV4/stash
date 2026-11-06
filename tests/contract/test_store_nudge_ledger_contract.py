from datetime import timedelta

import pytest
from builders import (
    BASE,
    FALL_BACK_DAY,
    LATER,
    NAIVE,
    PLUS_FIVE,
    SPRING_FORWARD_DAY,
    in_los_angeles,
)
from fakes.store_factories import StoreFactory, all_stores
from step_builders import DUE_AT, a_nudge

from stash.domain import NudgeKind

SPRING_FORWARD_MORNING = in_los_angeles(SPRING_FORWARD_DAY, 9)
FALL_BACK_MORNING = in_los_angeles(FALL_BACK_DAY, 9)
FALL_BACK_FIRST_PASS = in_los_angeles(FALL_BACK_DAY, 1, 30, fold=0)
FALL_BACK_SECOND_PASS = in_los_angeles(FALL_BACK_DAY, 1, 30, fold=1)


@all_stores
def test_a_nudge_that_was_never_recorded_was_not_sent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        sent = store.was_sent(a_nudge().key)

        # Assert
        assert sent is False


@all_stores
def test_a_recorded_nudge_was_sent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        nudge = a_nudge()
        store.record_sent(nudge, BASE)

        # Execute
        sent = store.was_sent(nudge.key)

        # Assert
        assert sent is True


@all_stores
def test_recording_a_new_nudge_reports_that_it_was_recorded(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        recorded = store.record_sent(a_nudge(), BASE)

        # Assert
        assert recorded is True


@all_stores
def test_recording_the_same_nudge_a_second_time_reports_that_it_was_already_recorded(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(), BASE)

        # Execute
        recorded = store.record_sent(a_nudge(), LATER)

        # Assert
        assert recorded is False


@all_stores
def test_recording_the_same_instant_in_another_offset_reports_that_it_was_already_recorded(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=DUE_AT), BASE)

        # Execute
        recorded = store.record_sent(a_nudge(due_at=DUE_AT.astimezone(PLUS_FIVE)), LATER)

        # Assert
        assert recorded is False


@all_stores
def test_recording_a_nudge_twice_keeps_the_first_send_time(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(), BASE)
        store.record_sent(a_nudge(), LATER)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last == BASE


@all_stores
def test_recording_a_nudge_again_earlier_still_keeps_the_first_send_time(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(), LATER)
        store.record_sent(a_nudge(), BASE)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last == LATER


@all_stores
def test_the_same_instant_written_in_another_offset_is_the_same_nudge(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=DUE_AT.astimezone(PLUS_FIVE)), BASE)

        # Execute
        sent = store.was_sent(a_nudge(due_at=DUE_AT).key)

        # Assert
        assert sent is True


@all_stores
def test_recording_the_same_instant_in_another_offset_keeps_the_first_send_time(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=DUE_AT), BASE)
        store.record_sent(a_nudge(due_at=DUE_AT.astimezone(PLUS_FIVE)), LATER)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last == BASE


@all_stores
def test_a_nudge_of_another_kind_is_a_different_nudge(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(kind=NudgeKind.STEP), BASE)

        # Execute
        sent = store.was_sent(a_nudge(kind=NudgeKind.ITEM_DATE).key)

        # Assert
        assert sent is False


@all_stores
def test_a_nudge_for_another_subject_is_a_different_nudge(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(subject_id="s1"), BASE)

        # Execute
        sent = store.was_sent(a_nudge(subject_id="s2").key)

        # Assert
        assert sent is False


@all_stores
def test_a_nudge_due_at_another_instant_is_a_different_nudge(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=DUE_AT), BASE)

        # Execute
        sent = store.was_sent(a_nudge(due_at=DUE_AT + timedelta(hours=1)).key)

        # Assert
        assert sent is False


@all_stores
def test_a_nudge_due_a_day_apart_in_one_zone_across_a_clock_change_is_a_different_nudge(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=SPRING_FORWARD_MORNING), BASE)

        # Execute
        sent = store.was_sent(a_nudge(due_at=FALL_BACK_MORNING).key)

        # Assert
        assert sent is False


@all_stores
def test_the_two_passes_over_a_repeated_local_hour_are_different_nudges(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=FALL_BACK_FIRST_PASS), BASE)

        # Execute
        sent = store.was_sent(a_nudge(due_at=FALL_BACK_SECOND_PASS).key)

        # Assert
        assert sent is False


@all_stores
def test_a_recorded_dst_nudge_was_sent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(due_at=FALL_BACK_MORNING), BASE)

        # Execute
        sent = store.was_sent(a_nudge(due_at=FALL_BACK_MORNING).key)

        # Assert
        assert sent is True


@all_stores
def test_last_sent_is_none_when_nothing_was_recorded(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        last = store.last_sent(NudgeKind.DIGEST)

        # Assert
        assert last is None


@all_stores
def test_last_sent_ignores_nudges_of_other_kinds(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(kind=NudgeKind.STEP), BASE)

        # Execute
        last = store.last_sent(NudgeKind.DIGEST)

        # Assert
        assert last is None


@all_stores
def test_last_sent_is_the_latest_send_time_of_the_kind(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(kind=NudgeKind.DIGEST, subject_id="d2"), LATER)
        store.record_sent(a_nudge(kind=NudgeKind.DIGEST, subject_id="d1"), BASE)
        store.record_sent(a_nudge(kind=NudgeKind.STEP, subject_id="s1"), LATER + timedelta(days=1))

        # Execute
        last = store.last_sent(NudgeKind.DIGEST)

        # Assert
        assert last == LATER


@all_stores
def test_last_sent_compares_send_times_as_instants_across_offsets(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        later_instant_earlier_wall_clock = LATER
        earlier_instant_later_wall_clock = (BASE + timedelta(hours=1)).astimezone(PLUS_FIVE)
        store.record_sent(a_nudge(subject_id="s1"), later_instant_earlier_wall_clock)
        store.record_sent(a_nudge(subject_id="s2"), earlier_instant_later_wall_clock)

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last == LATER


@all_stores
def test_last_sent_returns_an_aware_utc_datetime(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.record_sent(a_nudge(), BASE.astimezone(PLUS_FIVE))

        # Execute
        last = store.last_sent(NudgeKind.STEP)

        # Assert
        assert last is not None and last.utcoffset() == timedelta(0)


@all_stores
def test_a_nudge_recorded_with_a_naive_send_time_was_not_sent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with pytest.raises(ValueError, match="sent_at"):
            store.record_sent(a_nudge(), NAIVE)

        # Execute
        sent = store.was_sent(a_nudge().key)

        # Assert
        assert sent is False
