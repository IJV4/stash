from collections.abc import Iterable, Sequence

from fakes.recording_intake import RecordingIntake

from stash.capture import ProcessResult
from stash.domain import RawCapture


class PendingIntake(RecordingIntake):
    def __init__(self, results: Sequence[ProcessResult] = ()) -> None:
        super().__init__()
        self.results = list(results)

    def retry_pending(self, limit: int | None = None) -> list[ProcessResult]:
        self.calls.append("retry_pending")
        return list(self.results)

    def retry(self, captures: Iterable[RawCapture]) -> list[ProcessResult]:
        return self.retry_pending()
