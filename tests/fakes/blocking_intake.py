import threading

from builders import a_capture
from threads import OverlapGate

from stash.capture import (
    Deferred,
    Duplicate,
    Filed,
    IncomingMessage,
    IsRequest,
    ProcessResult,
    is_forced_request,
)
from stash.domain import CaptureStatus, RawCapture


class BlockingIntake:
    def __init__(self) -> None:
        self._gate = OverlapGate()
        self.release: threading.Event = self._gate.release
        self.entered: threading.Event = self._gate.entered
        self.overlapped: threading.Event = self._gate.overlapped

    @property
    def max_inside(self) -> int:
        return self._gate.max_inside

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        return a_capture()

    def process(self, capture: RawCapture) -> ProcessResult:
        if is_forced_request(capture):
            return IsRequest(capture.with_status(CaptureStatus.REQUEST))
        self._gate.hold()
        return Duplicate()

    def process_agent(self, capture: RawCapture) -> Filed | Deferred:
        self._gate.hold()
        return Deferred(capture, "ai_unavailable")

    def handle(self, message: IncomingMessage) -> ProcessResult:
        self._gate.hold()
        return Duplicate()

    def retry_pending(self) -> list[ProcessResult]:
        self._gate.hold()
        return []
