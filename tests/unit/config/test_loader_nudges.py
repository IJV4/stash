import dataclasses
import datetime as dt
from itertools import takewhile
from pathlib import Path

import pytest
from config_toml import a_toml, load, load_message, with_key, with_nudges

from stash.config import MAX_NUDGE_DAYS, MAX_TICK_SECONDS, NudgeConfig, Weekday
from stash.config.loader import load_config

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "deploy" / "stash.toml.example"
NUDGES_BLOCK_LINE_COUNT = 8

TIME_KEYS = ("digest_time", "reminder_time", "followup_time")
COUNT_BOUNDS = (
    ("forgotten_after_days", MAX_NUDGE_DAYS),
    ("stuck_doing_days", MAX_NUDGE_DAYS),
    ("tick_seconds", MAX_TICK_SECONDS),
)
BAD_TIME_LITERALS = [
    pytest.param('"25:00"', id="not-a-time"),
    pytest.param("10:00:00", id="native-toml-time"),
    pytest.param("10", id="integer"),
]
NON_INTEGER_LITERALS = [
    pytest.param("1.5", id="float"),
    pytest.param("true", id="true"),
    pytest.param("false", id="false"),
    pytest.param('"30"', id="string"),
]
BAD_DAY_LITERALS = [
    pytest.param('"funday"', id="unknown-name"),
    pytest.param('"Sunday"', id="capitalised"),
    pytest.param('"SUNDAY"', id="upper-case"),
    pytest.param('""', id="empty"),
    pytest.param("3", id="integer"),
    pytest.param("true", id="boolean"),
]
SINGLE_KEY_OVERRIDES = [
    pytest.param("digest_day", '"friday"', Weekday.FRIDAY, id="digest_day"),
    pytest.param("digest_time", '"18:30"', dt.time(18, 30), id="digest_time"),
    pytest.param("reminder_time", '"07:15"', dt.time(7, 15), id="reminder_time"),
    pytest.param("followup_time", '"08:45"', dt.time(8, 45), id="followup_time"),
    pytest.param("forgotten_after_days", "14", 14, id="forgotten_after_days"),
    pytest.param("stuck_doing_days", "10", 10, id="stuck_doing_days"),
    pytest.param("tick_seconds", "5", 5, id="tick_seconds"),
]
OUT_OF_RANGE_COUNTS = [
    pytest.param(key, literal, id=f"{key}={literal}")
    for key, upper in COUNT_BOUNDS
    for literal in ("0", "-1", str(upper + 1))
]
COUNT_BOUNDARIES = [
    pytest.param(key, bound, id=f"{key}={bound}")
    for key, upper in COUNT_BOUNDS
    for bound in (1, upper)
]


def test_without_a_nudges_table_every_value_is_its_default(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.nudges == NudgeConfig()


def test_an_empty_nudges_table_leaves_every_value_default(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_nudges(""))

    # Assert
    assert config.nudges == NudgeConfig()


def test_the_defaults_are_a_sunday_ten_oclock_digest_nine_oclock_reminders_and_a_minute_tick(
    tmp_path: Path,
) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert dataclasses.astuple(config.nudges) == (
        Weekday.SUNDAY,
        dt.time(10, 0),
        dt.time(9, 0),
        dt.time(9, 0),
        30,
        21,
        60,
    )


def test_a_full_nudges_table_overrides_every_key(tmp_path: Path) -> None:
    # Setup
    table = (
        'digest_day = "friday"\ndigest_time = "18:30"\nreminder_time = "07:15"\n'
        'followup_time = "08:45"\nforgotten_after_days = 14\nstuck_doing_days = 10\n'
        "tick_seconds = 5"
    )

    # Execute
    config = load(tmp_path, with_nudges(table))

    # Assert
    assert dataclasses.astuple(config.nudges) == (
        Weekday.FRIDAY,
        dt.time(18, 30),
        dt.time(7, 15),
        dt.time(8, 45),
        14,
        10,
        5,
    )


@pytest.mark.parametrize(("key", "literal", "value"), SINGLE_KEY_OVERRIDES)
def test_a_partial_nudges_table_overrides_one_key_and_the_others_keep_their_defaults(
    tmp_path: Path, key: str, literal: str, value: object
) -> None:
    # Execute
    config = load(tmp_path, with_nudges(f"{key} = {literal}"))

    # Assert
    assert config.nudges == NudgeConfig(**{key: value})


@pytest.mark.parametrize("weekday", list(Weekday), ids=[day.value for day in Weekday])
def test_every_lowercase_weekday_name_loads_as_its_weekday(
    tmp_path: Path, weekday: Weekday
) -> None:
    # Execute
    config = load(tmp_path, with_nudges(f'digest_day = "{weekday.value}"'))

    # Assert
    assert config.nudges.digest_day is weekday


@pytest.mark.parametrize("key", TIME_KEYS)
@pytest.mark.parametrize("literal", BAD_TIME_LITERALS)
def test_a_time_that_is_not_hh_mm_names_its_key(tmp_path: Path, key: str, literal: str) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges(f"{key} = {literal}"))

    # Assert
    assert f"nudges.{key}" in message


@pytest.mark.parametrize("key", TIME_KEYS)
@pytest.mark.parametrize(
    ("text", "expected"),
    [("00:00", dt.time(0, 0)), ("23:59", dt.time(23, 59))],
    ids=["midnight", "last-minute-of-the-day"],
)
def test_the_boundary_times_load(tmp_path: Path, key: str, text: str, expected: dt.time) -> None:
    # Execute
    config = load(tmp_path, with_nudges(f'{key} = "{text}"'))

    # Assert
    assert getattr(config.nudges, key) == expected


@pytest.mark.parametrize("literal", BAD_DAY_LITERALS)
def test_a_digest_day_that_is_not_a_lowercase_weekday_name_names_its_key(
    tmp_path: Path, literal: str
) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges(f"digest_day = {literal}"))

    # Assert
    assert "nudges.digest_day" in message


@pytest.mark.parametrize("key", [key for key, _ in COUNT_BOUNDS])
@pytest.mark.parametrize("literal", NON_INTEGER_LITERALS)
def test_a_count_that_is_not_an_integer_says_so(tmp_path: Path, key: str, literal: str) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges(f"{key} = {literal}"))

    # Assert
    assert message == f"nudges.{key} must be an integer"


@pytest.mark.parametrize(("key", "literal"), OUT_OF_RANGE_COUNTS)
def test_a_count_outside_its_bounds_names_its_key(tmp_path: Path, key: str, literal: str) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges(f"{key} = {literal}"))

    # Assert
    assert f"nudges.{key}" in message


@pytest.mark.parametrize(("key", "bound"), COUNT_BOUNDARIES)
def test_a_count_at_its_lower_or_upper_bound_loads(tmp_path: Path, key: str, bound: int) -> None:
    # Execute
    config = load(tmp_path, with_nudges(f"{key} = {bound}"))

    # Assert
    assert getattr(config.nudges, key) == bound


def test_an_unknown_nudges_key_is_rejected_with_its_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges('digest_dya = "sunday"'))

    # Assert
    assert message == "unknown config key(s): nudges.digest_dya"


def test_the_purchase_cool_off_key_is_not_accepted_yet(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, with_nudges("purchase_cool_off_days = 14"))

    # Assert
    assert message == "unknown config key(s): nudges.purchase_cool_off_days"


def test_a_nudges_value_that_is_not_a_table_names_nudges(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(top="nudges = 3"))

    # Assert
    assert message == "nudges must be a table"


def test_the_example_file_loads_with_the_default_nudges() -> None:
    # Execute
    config = load_config(EXAMPLE_FILE, with_key())

    # Assert
    assert config.nudges == NudgeConfig()


def test_the_example_files_nudges_block_works_once_uncommented(tmp_path: Path) -> None:
    # Setup
    lines = EXAMPLE_FILE.read_text(encoding="utf-8").splitlines()
    first = lines.index("# [nudges]")
    block = list(takewhile(lambda line: line.startswith("# "), lines[first:]))
    assert len(block) == NUDGES_BLOCK_LINE_COUNT
    uncommented = [line.removeprefix("# ") for line in block]
    lines[first : first + len(block)] = uncommented

    # Execute
    config = load(tmp_path, "\n".join(lines), with_key())

    # Assert
    assert config.nudges == NudgeConfig()
