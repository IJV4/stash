from datetime import datetime


class FakeBusy:
    def __init__(self, busy: bool = False) -> None:
        self.busy = busy

    def is_busy(self, now: datetime) -> bool:
        return self.busy
