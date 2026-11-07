import threading
from collections.abc import Callable
from datetime import datetime

from stash.capture import Reply


def _nothing() -> None:
    return None


class ScriptedNudges:
    def __init__(
        self, action: Callable[[], None] = _nothing, replies: tuple[Reply, ...] = ()
    ) -> None:
        self._action = action
        self._replies = replies
        self.nows: list[datetime] = []
        self.threads: list[int] = []

    def deliver(self, now: datetime, send: Callable[[Reply], None]) -> None:
        self.nows.append(now)
        self.threads.append(threading.get_ident())
        self._action()
        for reply in self._replies:
            send(reply)


class ScriptedProposals:
    def __init__(self, action: Callable[[], None] = _nothing) -> None:
        self._action = action
        self.threads: list[int] = []

    def deliver(self, send: Callable[[Reply], None]) -> None:
        self.threads.append(threading.get_ident())
        self._action()
