from collections.abc import Sequence

from fakes.recording_intake import RecordingIntake

from stash.capture import ProcessResult


class PendingIntake(RecordingIntake):
    def __init__(self, results: Sequence[ProcessResult] = ()) -> None:
        super().__init__()
        self.results = list(results)

    def retry_pending(self) -> list[ProcessResult]:
        self.calls.append("retry_pending")
        return list(self.results)
