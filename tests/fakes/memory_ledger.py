import threading
from collections.abc import Sequence
from datetime import UTC, datetime

from stash.domain import Nudge, NudgeKey, NudgeKind, require_aware


class MemoryLedger:
    def __init__(self, lock: threading.RLock) -> None:
        self._lock = lock
        self._sent: dict[NudgeKey, datetime] = {}

    def was_sent(self, key: NudgeKey) -> bool:
        with self._lock:
            return key in self._sent

    def _record(self, nudge: Nudge, sent_at: datetime) -> bool:
        if nudge.key in self._sent:
            return False
        self._sent[nudge.key] = sent_at.astimezone(UTC)
        return True

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool:
        require_aware("sent_at", sent_at)
        with self._lock:
            return all([self._record(nudge, sent_at) for nudge in nudges])

    def last_sent(self, kind: NudgeKind) -> datetime | None:
        with self._lock:
            sent = [at for key, at in self._sent.items() if key.kind == kind.value]
        return max(sent, default=None)
