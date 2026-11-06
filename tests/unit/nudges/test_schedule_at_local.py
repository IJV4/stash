from datetime import UTC, date, datetime, time

from builders import FALL_BACK_DAY, SPRING_FORWARD_DAY
from nudge_builders import a_nudge_schedule

NINE_AM = time(9, 0)


def test_nine_in_the_morning_on_a_winter_day_is_five_in_the_afternoon_utc() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(date(2027, 2, 13), NINE_AM)

    # Assert
    assert instant == datetime(2027, 2, 13, 17, 0, tzinfo=UTC)


def test_nine_in_the_morning_the_day_the_clocks_go_forward_is_sixteen_hundred_utc() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(SPRING_FORWARD_DAY, NINE_AM)

    # Assert
    assert instant == datetime(2027, 3, 14, 16, 0, tzinfo=UTC)


def test_nine_in_the_morning_the_day_the_clocks_go_back_is_seventeen_hundred_utc() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(FALL_BACK_DAY, NINE_AM)

    # Assert
    assert instant == datetime(2027, 11, 7, 17, 0, tzinfo=UTC)


def test_a_time_inside_the_spring_forward_gap_reads_with_the_offset_before_the_transition() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(SPRING_FORWARD_DAY, time(2, 30))

    # Assert
    assert instant == datetime(2027, 3, 14, 10, 30, tzinfo=UTC)


def test_an_ambiguous_fall_back_time_is_its_first_occurrence() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(FALL_BACK_DAY, time(1, 30))

    # Assert
    assert instant == datetime(2027, 11, 7, 8, 30, tzinfo=UTC)


def test_the_instant_is_expressed_in_utc() -> None:
    # Execute
    instant = a_nudge_schedule().at_local(date(2027, 2, 13), NINE_AM)

    # Assert
    assert instant.tzinfo is UTC
