import datetime as dt
import logging
from collections.abc import Callable
from typing import Protocol

from stash.capture import Filed, ProcessResult, Reply
from stash.store.port import Store

logger = logging.getLogger(__name__)

AUTO_RETRY_BATCH = 3
AUTO_RETRY_LAST_KEY = "capture.auto_retry_last"
NEVER = dt.timedelta(0)
SEND_FAILED_LOG = "auto-retry summary send failed (%s); the captures are filed anyway"


class PendingRetrier(Protocol):
    def retry_pending(self, limit: int | None = None) -> list[ProcessResult]: ...


class PendingRetryDelivery:
    def __init__(
        self,
        pipeline: PendingRetrier,
        gate_busy: Callable[[dt.datetime], bool],
        store: Store,
        interval: dt.timedelta,
        batch: int,
    ) -> None:
        self._pipeline = pipeline
        self._gate_busy = gate_busy
        self._store = store
        self._interval = interval
        self._batch = batch

    def deliver(self, now: dt.datetime, send: Callable[[Reply], None]) -> None:
        if self._interval <= NEVER or not self._store.pending_captures():
            return
        if self._attempted_within_interval(now):
            return
        if self._gate_busy(now):
            return
        self._store.put_setting(AUTO_RETRY_LAST_KEY, now.isoformat())
        filed = [r for r in self._pipeline.retry_pending(self._batch) if isinstance(r, Filed)]
        if not filed:
            return
        try:
            send(_summary(filed))
        except Exception as error:
            logger.warning(SEND_FAILED_LOG, type(error).__name__)

    def _attempted_within_interval(self, now: dt.datetime) -> bool:
        last = self._store.get_setting(AUTO_RETRY_LAST_KEY)
        return last is not None and now - dt.datetime.fromisoformat(last) < self._interval


def _summary(filed: list[Filed]) -> Reply:
    lines = [f"Filed {len(filed)} waiting capture(s) now that the AI is free:"]
    lines.extend(f"- {result.item.title}" for result in filed)
    return Reply("\n".join(lines))
