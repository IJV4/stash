from stash.capture import CaptureIntake, IncomingMessage, ProcessResult
from stash.domain import RawCapture


class RaisingIntake:
    def __init__(
        self,
        inner: CaptureIntake,
        on_receive: Exception | None = None,
        on_process: Exception | None = None,
    ) -> None:
        self._inner = inner
        self._on_receive = on_receive
        self._on_process = on_process

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        if self._on_receive is not None:
            raise self._on_receive
        return self._inner.receive(message)

    def process(self, capture: RawCapture) -> ProcessResult:
        if self._on_process is not None:
            raise self._on_process
        return self._inner.process(capture)

    def handle(self, message: IncomingMessage) -> ProcessResult:
        return self._inner.handle(message)

    def retry_pending(self) -> list[ProcessResult]:
        return self._inner.retry_pending()
