import datetime as dt
import logging
from collections.abc import Callable
from typing import Protocol

from stash.capture import ASK_AGAIN, Filed, IsRequest, ProcessResult, Reply
from stash.domain import printable_and_clip
from stash.store.port import Store

logger = logging.getLogger(__name__)

AUTO_RETRY_BATCH = 3
AUTO_RETRY_LAST_KEY = "capture.auto_retry_last"
REQUEST_PREVIEW_CHARS = 60
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
        results = self._pipeline.retry_pending(self._batch)
        filed = [r for r in results if isinstance(r, Filed)]
        requests = [r for r in results if isinstance(r, IsRequest)]
        if not filed and not requests:
            return
        try:
            send(_summary(filed, requests))
        except Exception as error:
            logger.warning(SEND_FAILED_LOG, type(error).__name__)

    def _attempted_within_interval(self, now: dt.datetime) -> bool:
        last = self._store.get_setting(AUTO_RETRY_LAST_KEY)
        return last is not None and now - dt.datetime.fromisoformat(last) < self._interval


def _summary(filed: list[Filed], requests: list[IsRequest]) -> Reply:
    lines: list[str] = []
    if filed:
        lines.append(f"Filed {len(filed)} waiting capture(s) now that the AI is free:")
        lines.extend(
            f"- {result.item.title}{ASK_AGAIN if result.unsure else ''}" for result in filed
        )
    lines.extend(
        f"- request — {printable_and_clip(result.capture.text, REQUEST_PREVIEW_CHARS)}{ASK_AGAIN}"
        for result in requests
    )
    return Reply("\n".join(lines))
