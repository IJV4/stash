from datetime import UTC, date, datetime, time, timedelta

from builders import MICROSECOND, in_los_angeles
from nudge_builders import SUNDAY, SUNDAY_DIGEST_TIME, a_nudge_schedule

from stash.config import Weekday

SUNDAY_FEB_7 = date(2027, 2, 7)
SUNDAY_FEB_21 = date(2027, 2, 21)


def test_a_span_with_one_sunday_has_that_sundays_digest_instant() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        in_los_angeles(date(2027, 2, 12)), in_los_angeles(date(2027, 2, 15))
    )

    # Assert
    assert instants == [SUNDAY_DIGEST_TIME]


def test_a_span_without_a_sunday_has_no_digest_instant() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        in_los_angeles(date(2027, 2, 15)), in_los_angeles(date(2027, 2, 20))
    )

    # Assert
    assert instants == []


def test_a_digest_instant_exactly_at_the_start_of_the_span_is_included() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        SUNDAY_DIGEST_TIME, SUNDAY_DIGEST_TIME + timedelta(days=1)
    )

    # Assert
    assert instants == [SUNDAY_DIGEST_TIME]


def test_a_digest_instant_a_microsecond_before_the_start_of_the_span_is_excluded() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        SUNDAY_DIGEST_TIME + MICROSECOND, SUNDAY_DIGEST_TIME + timedelta(days=1)
    )

    # Assert
    assert instants == []


def test_a_digest_instant_exactly_at_the_end_of_the_span_is_included() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        SUNDAY_DIGEST_TIME - timedelta(days=1), SUNDAY_DIGEST_TIME
    )

    # Assert
    assert instants == [SUNDAY_DIGEST_TIME]


def test_a_digest_instant_a_microsecond_after_the_end_of_the_span_is_excluded() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        SUNDAY_DIGEST_TIME - timedelta(days=1), SUNDAY_DIGEST_TIME - MICROSECOND
    )

    # Assert
    assert instants == []


def test_two_sundays_in_the_span_give_their_digest_instants_oldest_first() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        in_los_angeles(SUNDAY_FEB_7), in_los_angeles(SUNDAY_FEB_21)
    )

    # Assert
    assert instants == [in_los_angeles(SUNDAY_FEB_7, 10), SUNDAY_DIGEST_TIME]


def test_a_utc_sunday_that_is_still_saturday_evening_in_los_angeles_has_no_digest_instant() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        in_los_angeles(date(2027, 2, 13), 20), in_los_angeles(SUNDAY, 9, 59)
    )

    # Assert
    assert instants == []


def test_the_digest_instants_across_the_clocks_going_forward_follow_the_local_offset() -> None:
    # Execute
    instants = a_nudge_schedule().digest_instants_between(
        in_los_angeles(date(2027, 3, 6)), in_los_angeles(date(2027, 3, 15))
    )

    # Assert
    assert instants == [
        datetime(2027, 3, 7, 18, 0, tzinfo=UTC),
        datetime(2027, 3, 14, 17, 0, tzinfo=UTC),
    ]


def test_the_configured_digest_day_and_time_decide_the_digest_instants() -> None:
    # Setup
    schedule = a_nudge_schedule(digest_day=Weekday.WEDNESDAY, digest_time=time(8, 30))

    # Execute
    instants = schedule.digest_instants_between(
        in_los_angeles(date(2027, 2, 15)), in_los_angeles(date(2027, 2, 20))
    )

    # Assert
    assert instants == [in_los_angeles(date(2027, 2, 17), 8, 30)]


def test_the_latest_digest_in_a_span_with_two_sundays_is_the_later_one() -> None:
    # Execute
    instant = a_nudge_schedule().latest_digest_between(
        in_los_angeles(SUNDAY_FEB_7), in_los_angeles(SUNDAY_FEB_21)
    )

    # Assert
    assert instant == SUNDAY_DIGEST_TIME


def test_a_span_without_a_digest_instant_has_no_latest_digest() -> None:
    # Execute
    instant = a_nudge_schedule().latest_digest_between(
        in_los_angeles(date(2027, 2, 15)), in_los_angeles(date(2027, 2, 20))
    )

    # Assert
    assert instant is None
