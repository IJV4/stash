import threading

from stash.capture import IncomingMessage, ProcessResult
from stash.domain import RawCapture
from stash.hermes_adapter.ports import IntakeSteps

HOLD_LIMIT_SECONDS = 5.0


class ScriptedSteps:
    def __init__(
        self,
        inner: IntakeSteps,
        *,
        receive_failure: Exception | None = None,
        process_failure: Exception | None = None,
        process_result: ProcessResult | None = None,
        process_gate: threading.Event | None = None,
    ) -> None:
        self._inner = inner
        self._receive_failure = receive_failure
        self._process_failure = process_failure
        self._process_result = process_result
        self._process_gate = process_gate
        self.calls: list[tuple[str, str]] = []
        self.received: list[IncomingMessage] = []
        self.processed: list[RawCapture] = []
        self.receive_threads: list[int] = []
        self.process_threads: list[int] = []

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        self.calls.append(("receive", message.text))
        self.received.append(message)
        self.receive_threads.append(threading.get_ident())
        if self._receive_failure is not None:
            raise self._receive_failure
        return self._inner.receive(message)

    def process(self, capture: RawCapture) -> ProcessResult:
        self.calls.append(("process", capture.text))
        self.processed.append(capture)
        self.process_threads.append(threading.get_ident())
        if self._process_gate is not None:
            self._process_gate.wait(HOLD_LIMIT_SECONDS)
        if self._process_failure is not None:
            raise self._process_failure
        if self._process_result is not None:
            return self._process_result
        return self._inner.process(capture)
