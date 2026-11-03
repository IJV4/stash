from datetime import datetime


class FakeBusy:
    def __init__(self, busy: bool = False) -> None:
        self.busy = busy

    def is_busy(self, now: datetime) -> bool:
        return self.busy


class BusyUntil:
    def __init__(self, deadline: datetime) -> None:
        self._deadline = deadline

    def is_busy(self, now: datetime) -> bool:
        return now < self._deadline
