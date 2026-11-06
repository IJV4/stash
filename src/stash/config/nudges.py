import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from stash.config.errors import ConfigError

MAX_NUDGE_DAYS = 365
MAX_TICK_SECONDS = 3600
MIN_NUDGE_VALUE = 1


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @property
    def python_weekday(self) -> int:
        return _PYTHON_WEEKDAYS[self]


_PYTHON_WEEKDAYS = MappingProxyType(
    {
        Weekday.MONDAY: 0,
        Weekday.TUESDAY: 1,
        Weekday.WEDNESDAY: 2,
        Weekday.THURSDAY: 3,
        Weekday.FRIDAY: 4,
        Weekday.SATURDAY: 5,
        Weekday.SUNDAY: 6,
    }
)

DEFAULT_DIGEST_DAY = Weekday.SUNDAY
DEFAULT_DIGEST_TIME = dt.time(10, 0)
DEFAULT_REMINDER_TIME = dt.time(9, 0)
DEFAULT_FOLLOWUP_TIME = dt.time(9, 0)
DEFAULT_FORGOTTEN_AFTER_DAYS = 30
DEFAULT_STUCK_DOING_DAYS = 21
DEFAULT_TICK_SECONDS = 60


@dataclass(frozen=True, slots=True)
class NudgeConfig:
    digest_day: Weekday = DEFAULT_DIGEST_DAY
    digest_time: dt.time = DEFAULT_DIGEST_TIME
    reminder_time: dt.time = DEFAULT_REMINDER_TIME
    followup_time: dt.time = DEFAULT_FOLLOWUP_TIME
    forgotten_after_days: int = DEFAULT_FORGOTTEN_AFTER_DAYS
    stuck_doing_days: int = DEFAULT_STUCK_DOING_DAYS
    tick_seconds: int = DEFAULT_TICK_SECONDS

    def __post_init__(self) -> None:
        self._require_whole_minute("digest_time", self.digest_time)
        self._require_whole_minute("reminder_time", self.reminder_time)
        self._require_whole_minute("followup_time", self.followup_time)
        self._require_within("forgotten_after_days", self.forgotten_after_days, MAX_NUDGE_DAYS)
        self._require_within("stuck_doing_days", self.stuck_doing_days, MAX_NUDGE_DAYS)
        self._require_within("tick_seconds", self.tick_seconds, MAX_TICK_SECONDS)

    @staticmethod
    def _require_whole_minute(key: str, value: dt.time) -> None:
        if value.tzinfo is not None or value.second != 0 or value.microsecond != 0:
            raise ConfigError(f"nudges.{key} must be a whole-minute time without a time zone")

    @staticmethod
    def _require_within(key: str, value: int, maximum: int) -> None:
        if not MIN_NUDGE_VALUE <= value <= maximum:
            raise ConfigError(f"nudges.{key} must be between {MIN_NUDGE_VALUE} and {maximum}")
