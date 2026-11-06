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
        self.crash_after: int | None = None

    def record_sent(self, nudge: Nudge, sent_at: datetime) -> bool:
        if nudge.kind is self.crash_on or self._crash_after_reached():
            raise LedgerCrashed(nudge.kind)
        self.recorded.append(nudge.kind)
        return super().record_sent(nudge, sent_at)

    def _crash_after_reached(self) -> bool:
        return self.crash_after is not None and len(self.recorded) >= self.crash_after
