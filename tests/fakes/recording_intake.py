from builders import a_capture

from stash.capture import Duplicate, IncomingMessage, ProcessResult
from stash.domain import RawCapture


class RecordingIntake:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.capture = a_capture()
        self.result: ProcessResult = Duplicate()
        self.fail_next: Exception | None = None

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        self.calls.append("receive")
        return self.capture

    def process(self, capture: RawCapture) -> ProcessResult:
        self.calls.append("process")
        self._fail_once()
        return self.result

    def handle(self, message: IncomingMessage) -> ProcessResult:
        self.calls.append("handle")
        self._fail_once()
        return self.result

    def retry_pending(self) -> list[ProcessResult]:
        self.calls.append("retry_pending")
        self._fail_once()
        return [self.result]

    def _fail_once(self) -> None:
        if self.fail_next is not None:
            failure, self.fail_next = self.fail_next, None
            raise failure
