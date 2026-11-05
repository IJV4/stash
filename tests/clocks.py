from datetime import datetime, timedelta

from builders import BASE


class SettableClock:
    def __init__(self, now: datetime = BASE) -> None:
        self._now = now

    def __call__(self) -> datetime:
        return self._now

    def advance(self, by: timedelta) -> None:
        self._now += by
