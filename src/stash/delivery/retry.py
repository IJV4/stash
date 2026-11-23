import datetime as dt
import logging
from collections.abc import Callable, Iterable
from typing import Protocol

from stash.capture import ASK_AGAIN, Filed, IsRequest, ProcessResult, Reply
from stash.domain import RawCapture, printable_and_clip
from stash.store.port import Store

logger = logging.getLogger(__name__)

AUTO_RETRY_BATCH = 3
AUTO_RETRY_LAST_KEY = "capture.auto_retry_last"
AUTO_RETRY_CURSOR_KEY = "capture.auto_retry_cursor"
CURSOR_SEPARATOR = "|"
REQUEST_PREVIEW_CHARS = 60
NEVER = dt.timedelta(0)
SEND_FAILED_LOG = "auto-retry summary send failed (%s); the captures are filed anyway"


class PendingRetrier(Protocol):
    def retry(self, captures: Iterable[RawCapture]) -> list[ProcessResult]: ...


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
        batch = self._next_batch()
        self._remember_cursor(batch[-1])
        results = self._pipeline.retry(batch)
        filed = [r for r in results if isinstance(r, Filed)]
        requests = [r for r in results if isinstance(r, IsRequest)]
        if not filed and not requests:
            return
        try:
            send(_summary(filed, requests))
        except Exception as error:
            logger.warning(SEND_FAILED_LOG, type(error).__name__)

    def _next_batch(self) -> list[RawCapture]:
        pending = self._store.pending_captures()
        cursor = self._cursor()
        if cursor is not None:
            pending = [c for c in pending if _position(c) > cursor] + [
                c for c in pending if _position(c) <= cursor
            ]
        return pending[: self._batch]

    def _cursor(self) -> tuple[dt.datetime, str] | None:
        stored = self._store.get_setting(AUTO_RETRY_CURSOR_KEY)
        if stored is None:
            return None
        received, _, capture_id = stored.partition(CURSOR_SEPARATOR)
        return dt.datetime.fromisoformat(received), capture_id

    def _remember_cursor(self, last: RawCapture) -> None:
        received, capture_id = _position(last)
        self._store.put_setting(
            AUTO_RETRY_CURSOR_KEY, f"{received.isoformat()}{CURSOR_SEPARATOR}{capture_id}"
        )

    def _attempted_within_interval(self, now: dt.datetime) -> bool:
        last = self._store.get_setting(AUTO_RETRY_LAST_KEY)
        return last is not None and now - dt.datetime.fromisoformat(last) < self._interval


def _position(capture: RawCapture) -> tuple[dt.datetime, str]:
    return capture.received_at, capture.id


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
