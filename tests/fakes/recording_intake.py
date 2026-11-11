from builders import a_capture

from stash.capture import DeferralReason, Deferred, Duplicate, Filed, IncomingMessage, ProcessResult
from stash.domain import RawCapture


class RecordingIntake:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.messages: list[IncomingMessage] = []
        self.capture = a_capture()
        self.result: ProcessResult = Duplicate()
        self.agent_result: Filed | Deferred = Deferred(self.capture, DeferralReason.AI_UNAVAILABLE)
        self.fail_next: Exception | None = None
        self.receive_error: Exception | None = None
        self.duplicate = False

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        self.calls.append("receive")
        self.messages.append(message)
        if self.receive_error is not None:
            raise self.receive_error
        return None if self.duplicate else self.capture

    def process(self, capture: RawCapture) -> ProcessResult:
        self.calls.append("process")
        self._fail_once()
        return self.result

    def process_agent(self, capture: RawCapture) -> Filed | Deferred:
        self.calls.append("process_agent")
        self._fail_once()
        return self.agent_result

    def handle(self, message: IncomingMessage) -> ProcessResult:
        self.calls.append("handle")
        self.messages.append(message)
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
