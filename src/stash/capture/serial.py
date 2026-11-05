import threading

from stash.capture.message import IncomingMessage
from stash.capture.ports import CaptureIntake
from stash.capture.results import ProcessResult
from stash.capture.routing import forces_request
from stash.domain import RawCapture


class SerializedPipeline:
    def __init__(self, inner: CaptureIntake) -> None:
        self._inner = inner
        self._turn = threading.Lock()

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        return self._inner.receive(message)

    def process(self, capture: RawCapture) -> ProcessResult:
        # No turn: a forced request makes no AI call, so it must not queue behind a classification.
        if forces_request(capture.text):
            return self._inner.process(capture)
        with self._turn:
            return self._inner.process(capture)

    def handle(self, message: IncomingMessage) -> ProcessResult:
        with self._turn:
            return self._inner.handle(message)

    def retry_pending(self) -> list[ProcessResult]:
        with self._turn:
            return self._inner.retry_pending()
