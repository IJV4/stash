from datetime import datetime, timedelta

from builders import MICROSECOND, stored
from fakes.memory_store import MemoryStore
from nudge_builders import (
    LONG_AGO,
    SUNDAY_DIGEST_TIME,
    SUNDAY_NOON,
    a_nudger,
    a_stuck_book,
    only,
)

from stash.nudges import StuckItem, WeeklyDigest
from stash.store import Store

PREVIOUS_SUNDAY_DIGEST_TIME = SUNDAY_DIGEST_TIME - timedelta(days=7)


def digests(store: Store, now: datetime, **config: object) -> list[WeeklyDigest]:
    return only(WeeklyDigest, a_nudger(store, **config).due(now))


def test_the_digest_is_due_at_the_digest_time_on_the_digest_day() -> None:
    # Setup
    store = MemoryStore()

    # Execute
    due = digests(store, SUNDAY_DIGEST_TIME)

    # Assert
    assert due == [WeeklyDigest(SUNDAY_DIGEST_TIME, ())]


def test_just_before_the_digest_time_the_latest_unsent_digest_is_last_weeks() -> None:
    # Setup
    store = MemoryStore()

    # Execute
    due = digests(store, SUNDAY_DIGEST_TIME - MICROSECOND)

    # Assert
    assert [digest.due_at for digest in due] == [PREVIOUS_SUNDAY_DIGEST_TIME]


def test_with_two_digest_instants_in_the_window_only_the_latest_is_due() -> None:
    # Setup
    store = MemoryStore()

    # Execute
    due = digests(store, SUNDAY_NOON)

    # Assert
    assert [digest.due_at for digest in due] == [SUNDAY_DIGEST_TIME]


def test_when_the_latest_digest_was_sent_the_older_unsent_one_is_not_offered() -> None:
    # Setup
    store = MemoryStore()
    store.record_sent(WeeklyDigest(SUNDAY_DIGEST_TIME, ()).nudge, SUNDAY_DIGEST_TIME)

    # Execute
    due = digests(store, SUNDAY_NOON)

    # Assert
    assert due == []


def test_when_the_latest_digest_is_unsent_and_the_older_one_was_sent_the_latest_is_due() -> None:
    # Setup
    store = MemoryStore()
    store.record_sent(WeeklyDigest(PREVIOUS_SUNDAY_DIGEST_TIME, ()).nudge, LONG_AGO)

    # Execute
    due = digests(store, SUNDAY_NOON)

    # Assert
    assert [digest.due_at for digest in due] == [SUNDAY_DIGEST_TIME]


def test_a_doing_item_not_updated_for_the_stuck_period_rides_the_digest() -> None:
    # Setup
    store = MemoryStore()
    book = stored(store, a_stuck_book())

    # Execute
    due = digests(store, SUNDAY_DIGEST_TIME)

    # Assert
    assert due == [WeeklyDigest(SUNDAY_DIGEST_TIME, (StuckItem(book, SUNDAY_DIGEST_TIME),))]


def test_stuck_items_are_never_due_without_their_digest() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book())
    store.record_sent(WeeklyDigest(SUNDAY_DIGEST_TIME, ()).nudge, SUNDAY_DIGEST_TIME)

    # Execute
    due = a_nudger(store).due(SUNDAY_NOON)

    # Assert
    assert due == []


def test_a_doing_item_updated_within_the_stuck_period_is_not_stuck() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book(updated_at=SUNDAY_DIGEST_TIME - timedelta(days=6)))

    # Execute
    due = digests(store, SUNDAY_DIGEST_TIME, stuck_doing_days=7)

    # Assert
    assert due == [WeeklyDigest(SUNDAY_DIGEST_TIME, ())]


def test_a_doing_item_updated_exactly_the_stuck_period_before_the_digest_is_not_stuck() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book(updated_at=SUNDAY_DIGEST_TIME - timedelta(days=7)))

    # Execute
    [digest] = digests(store, SUNDAY_DIGEST_TIME, stuck_doing_days=7)

    # Assert
    assert digest.stuck == ()


def test_a_doing_item_updated_a_microsecond_more_than_the_stuck_period_before_is_stuck() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book(updated_at=SUNDAY_DIGEST_TIME - timedelta(days=7) - MICROSECOND))

    # Execute
    [digest] = digests(store, SUNDAY_DIGEST_TIME, stuck_doing_days=7)

    # Assert
    assert len(digest.stuck) == 1


def test_a_doing_item_updated_before_the_configured_stuck_period_is_stuck() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book(updated_at=SUNDAY_DIGEST_TIME - timedelta(days=8)))

    # Execute
    [digest] = digests(store, SUNDAY_DIGEST_TIME, stuck_doing_days=7)

    # Assert
    assert len(digest.stuck) == 1


def test_stuckness_is_judged_at_the_digest_instant_not_at_the_time_of_the_check() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_stuck_book(updated_at=SUNDAY_DIGEST_TIME - timedelta(days=20)))

    # Execute
    [digest] = digests(store, SUNDAY_DIGEST_TIME + timedelta(days=2))

    # Assert
    assert digest.stuck == ()


def test_a_stuck_item_already_sent_with_an_earlier_attempt_is_left_out_of_the_digest() -> None:
    # Setup
    store = MemoryStore()
    book = stored(store, a_stuck_book())
    store.record_sent(StuckItem(book, SUNDAY_DIGEST_TIME).nudge, SUNDAY_DIGEST_TIME)

    # Execute
    due = digests(store, SUNDAY_DIGEST_TIME)

    # Assert
    assert due == [WeeklyDigest(SUNDAY_DIGEST_TIME, ())]


def test_at_most_ten_stuck_items_ride_the_digest() -> None:
    # Setup
    store = MemoryStore()
    for number in range(11):
        stored(store, a_stuck_book(id=f"book-{number}"))

    # Execute
    [digest] = digests(store, SUNDAY_DIGEST_TIME)

    # Assert
    assert len(digest.stuck) == 10
