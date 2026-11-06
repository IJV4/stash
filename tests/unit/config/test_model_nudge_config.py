import dataclasses
import datetime as dt

import pytest
from config_builders import a_nudge_config

from stash.config import MAX_NUDGE_DAYS, MAX_TICK_SECONDS, ConfigError, NudgeConfig, Weekday

TIME_FIELDS = ("digest_time", "reminder_time", "followup_time")
COUNT_FIELD_BOUNDS = (
    ("forgotten_after_days", MAX_NUDGE_DAYS),
    ("stuck_doing_days", MAX_NUDGE_DAYS),
    ("tick_seconds", MAX_TICK_SECONDS),
)
MONDAY_FIRST = (
    Weekday.MONDAY,
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
    Weekday.FRIDAY,
    Weekday.SATURDAY,
    Weekday.SUNDAY,
)
UNREPRESENTABLE_TIMES = [
    pytest.param(dt.time(10, 0, 30), id="seconds"),
    pytest.param(dt.time(10, 0, 0, 1), id="microseconds"),
    pytest.param(dt.time(10, 0, tzinfo=dt.UTC), id="timezone-aware"),
]
OUT_OF_RANGE_COUNTS = [
    pytest.param(field, value, id=f"{field}={value}")
    for field, upper in COUNT_FIELD_BOUNDS
    for value in (0, -1, upper + 1)
]
BOUNDARY_COUNTS = [
    pytest.param(field, value, id=f"{field}={value}")
    for field, upper in COUNT_FIELD_BOUNDS
    for value in (1, upper)
]


def test_the_weekdays_are_the_lowercase_english_names_monday_first() -> None:
    # Assert
    assert [day.value for day in Weekday] == [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]


@pytest.mark.parametrize(
    ("offset", "weekday"),
    [pytest.param(offset, day, id=day.value) for offset, day in enumerate(MONDAY_FIRST)],
)
def test_a_weekdays_python_weekday_is_the_number_date_weekday_uses(
    offset: int, weekday: Weekday
) -> None:
    # Assert
    assert weekday.python_weekday == dt.date(2026, 11, 2 + offset).weekday()


def test_the_day_count_bound_is_a_year() -> None:
    # Assert
    assert MAX_NUDGE_DAYS == 365


def test_the_tick_bound_is_an_hour() -> None:
    # Assert
    assert MAX_TICK_SECONDS == 3600


@pytest.mark.parametrize("field", [field.name for field in dataclasses.fields(NudgeConfig)])
def test_a_nudge_config_field_cannot_be_modified(field: str) -> None:
    # Setup
    nudges = a_nudge_config()

    # Execute / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(nudges, field, None)


def test_a_nudge_config_has_no_instance_dictionary() -> None:
    # Assert
    assert not hasattr(a_nudge_config(), "__dict__")


def test_a_nudge_config_built_with_no_arguments_equals_one_built_with_every_default() -> None:
    # Assert
    assert NudgeConfig() == a_nudge_config()


@pytest.mark.parametrize("field", TIME_FIELDS)
@pytest.mark.parametrize("value", UNREPRESENTABLE_TIMES)
def test_a_time_with_seconds_microseconds_or_a_timezone_names_its_field(
    field: str, value: dt.time
) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=f"nudges.{field}"):
        a_nudge_config(**{field: value})


@pytest.mark.parametrize("field", TIME_FIELDS)
def test_a_whole_minute_time_is_accepted(field: str) -> None:
    # Execute
    nudges = a_nudge_config(**{field: dt.time(23, 59)})

    # Assert
    assert getattr(nudges, field) == dt.time(23, 59)


@pytest.mark.parametrize(("field", "value"), OUT_OF_RANGE_COUNTS)
def test_a_count_outside_its_bounds_names_its_field(field: str, value: int) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=f"nudges.{field}"):
        a_nudge_config(**{field: value})


@pytest.mark.parametrize(("field", "value"), BOUNDARY_COUNTS)
def test_a_count_at_its_lower_or_upper_bound_is_accepted(field: str, value: int) -> None:
    # Execute
    nudges = a_nudge_config(**{field: value})

    # Assert
    assert getattr(nudges, field) == value
