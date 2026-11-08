import threading

from stash.enrich.links import LinkInfo

WAIT_FOR_START_SECONDS = 1.0
HOLD_LIMIT_SECONDS = 1.0


class HungLinkInspector:
    def __init__(self, answer: LinkInfo | None = None) -> None:
        self._answer = answer
        self.release = threading.Event()
        self._started = threading.Event()
        self._daemon: bool | None = None

    def inspect(self, url: str) -> LinkInfo:
        self._daemon = threading.current_thread().daemon
        self._started.set()
        self.release.wait(HOLD_LIMIT_SECONDS)
        return self._answer or LinkInfo.unknown(url)

    def ran_in_a_daemon_thread(self) -> bool | None:
        self._started.wait(WAIT_FOR_START_SECONDS)
        return self._daemon
