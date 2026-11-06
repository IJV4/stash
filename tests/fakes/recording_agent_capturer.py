from builders import a_capture, an_item

from stash.capture import Deferred, Filed


class RecordingAgentCapturer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.result: Filed | Deferred = Filed(an_item(), unsure=False)
        self.error: Exception | None = None

    def file(self, text: str, note: str | None = None) -> Filed | Deferred:
        self.calls.append((text, note))
        if self.error is not None:
            raise self.error
        return self.result

    def defers(self) -> None:
        self.result = Deferred(a_capture(), "ai_unavailable")
