from collections.abc import Sequence
from datetime import datetime

from fakes.memory_store import MemoryStore

from stash.domain import Nudge, NudgeKind


class LedgerCrashed(Exception):
    pass


class LedgerRecordingStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.recorded: list[NudgeKind] = []
        self.crash_on: NudgeKind | None = None

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool:
        if any(nudge.kind is self.crash_on for nudge in nudges):
            raise LedgerCrashed(self.crash_on)
        self.recorded.extend(nudge.kind for nudge in nudges)
        return super().record_all_sent(nudges, sent_at)
