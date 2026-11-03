import threading

from builders import a_capture

from stash.capture import Duplicate, IncomingMessage, ProcessResult
from stash.domain import RawCapture

HOLD_LIMIT_SECONDS = 1.0


class BlockingIntake:
    def __init__(self) -> None:
        self.release = threading.Event()
        self.entered = threading.Event()
        self.overlapped = threading.Event()
        self.max_inside = 0
        self._inside = 0
        self._counting = threading.Lock()

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        return a_capture()

    def process(self, capture: RawCapture) -> ProcessResult:
        self._hold()
        return Duplicate()

    def handle(self, message: IncomingMessage) -> ProcessResult:
        self._hold()
        return Duplicate()

    def retry_pending(self) -> list[ProcessResult]:
        self._hold()
        return []

    def _hold(self) -> None:
        with self._counting:
            self._inside += 1
            self.max_inside = max(self.max_inside, self._inside)
            if self._inside > 1:
                self.overlapped.set()
        self.entered.set()
        self.release.wait(HOLD_LIMIT_SECONDS)
        with self._counting:
            self._inside -= 1
