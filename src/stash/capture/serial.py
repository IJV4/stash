import threading
from collections.abc import Iterable

from stash.capture.message import IncomingMessage
from stash.capture.ports import CaptureIntake
from stash.capture.results import Deferred, Filed, ProcessResult
from stash.capture.routing import is_forced_request
from stash.domain import RawCapture


class SerializedPipeline:
    def __init__(self, inner: CaptureIntake) -> None:
        self._inner = inner
        self._turn = threading.Lock()

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        return self._inner.receive(message)

    def process(self, capture: RawCapture) -> ProcessResult:
        # No turn: a forced request makes no AI call, so it must not queue behind a classification.
        if is_forced_request(capture):
            return self._inner.process(capture)
        with self._turn:
            return self._inner.process(capture)

    def process_agent(self, capture: RawCapture) -> Filed | Deferred:
        with self._turn:
            return self._inner.process_agent(capture)

    def handle(self, message: IncomingMessage) -> ProcessResult:
        with self._turn:
            return self._inner.handle(message)

    def retry_pending(self, limit: int | None = None) -> list[ProcessResult]:
        with self._turn:
            return self._inner.retry_pending(limit)

    def retry(self, captures: Iterable[RawCapture]) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for capture in captures:
            with self._turn:
                results.extend(self._inner.retry([capture]))
        return results
