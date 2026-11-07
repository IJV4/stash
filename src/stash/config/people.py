from dataclasses import dataclass

from stash.config.errors import ConfigError
from stash.config.nudges import MAX_NUDGE_DAYS

DEFAULT_LEAD_DAYS = (14, 2, 0)


@dataclass(frozen=True, slots=True)
class PeopleConfig:
    lead_days: tuple[int, ...] = DEFAULT_LEAD_DAYS

    def __post_init__(self) -> None:
        if not self.lead_days:
            raise ConfigError("people.lead_days must list at least one lead time")
        if any(not 0 <= lead <= MAX_NUDGE_DAYS for lead in self.lead_days):
            raise ConfigError(f"people.lead_days must be between 0 and {MAX_NUDGE_DAYS}")
        if len(set(self.lead_days)) != len(self.lead_days):
            raise ConfigError("people.lead_days must not repeat a lead time")
