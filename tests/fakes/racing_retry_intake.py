from collections.abc import Iterable

from stash.capture import CaptureIntake, IncomingMessage, ProcessResult
from stash.domain import RawCapture


class RacingRetryIntake:
    def __init__(self, inner: CaptureIntake) -> None:
        self._inner = inner
        self.retried: list[list[ProcessResult]] = []

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        capture = self._inner.receive(message)
        self.retried.append(self._inner.retry_pending())
        return capture

    def process(self, capture: RawCapture) -> ProcessResult:
        return self._inner.process(capture)

    def handle(self, message: IncomingMessage) -> ProcessResult:
        return self._inner.handle(message)

    def retry_pending(self, limit: int | None = None) -> list[ProcessResult]:
        return self._inner.retry_pending(limit)

    def retry(self, captures: Iterable[RawCapture]) -> list[ProcessResult]:
        return self._inner.retry(captures)
