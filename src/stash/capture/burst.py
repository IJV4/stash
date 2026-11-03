from dataclasses import dataclass
from datetime import datetime, timedelta

from stash.capture.replies import Reply, reply_for, summary
from stash.capture.results import Deferred, Filed
from stash.domain import require_aware


def _key(result: Filed | Deferred) -> tuple[str, str]:
    if isinstance(result, Filed):
        return ("filed", result.item.id)
    return ("deferred", result.capture.id)


@dataclass(frozen=True, slots=True)
class _Batch:
    opened_at: datetime
    results: tuple[Filed | Deferred, ...]

    def holds(self, result: Filed | Deferred) -> bool:
        return _key(result) in {_key(held) for held in self.results}

    def with_result(self, result: Filed | Deferred) -> "_Batch":
        return _Batch(self.opened_at, (*self.results, result))

    def reply(self) -> Reply:
        return reply_for(self.results[0]) if len(self.results) == 1 else summary(self.results)


class BurstCoalescer:
    def __init__(self, window_seconds: float) -> None:
        if window_seconds < 0:
            raise ValueError("window_seconds must not be negative")
        self._window_seconds = float(window_seconds)
        self._window = timedelta(seconds=window_seconds)
        self._batch: _Batch | None = None

    @property
    def window_seconds(self) -> float:
        return self._window_seconds

    def add(self, result: Filed | Deferred, now: datetime) -> None:
        require_aware("now", now)
        if self._batch is None:
            self._batch = _Batch(now, (result,))
        elif not self._batch.holds(result):
            self._batch = self._batch.with_result(result)

    def due(self, now: datetime) -> Reply | None:
        require_aware("now", now)
        batch = self._batch
        if batch is None or now - batch.opened_at < self._window:
            return None
        reply = batch.reply()
        self._batch = None
        return reply
