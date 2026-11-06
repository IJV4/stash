from datetime import UTC, datetime, timedelta

from builders import BASE

EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


class SettableClock:
    def __init__(self, now: datetime = BASE) -> None:
        self._now = now

    def __call__(self) -> datetime:
        return self._now

    def advance(self, by: timedelta) -> None:
        self._now += by
