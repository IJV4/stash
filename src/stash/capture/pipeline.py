import logging
from collections.abc import Callable
from datetime import datetime

from stash.capture.message import IncomingMessage
from stash.capture.ports import CaptureFiler, IntakeStore
from stash.capture.results import (
    Deferred,
    Duplicate,
    Filed,
    IsRequest,
    ProcessResult,
)
from stash.capture.routing import forces_request
from stash.domain import CaptureStatus, Filing, Item, RawCapture, Route
from stash.enrich.links import LinkInspector
from stash.enrich.urls import extract_urls
from stash.llm.errors import LlmDeferred, LlmError

logger = logging.getLogger(__name__)


class CapturePipeline:
    def __init__(
        self,
        store: IntakeStore,
        inspector: LinkInspector,
        filer: CaptureFiler,
        new_id: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> None:
        self._store = store
        self._inspector = inspector
        self._filer = filer
        self._new_id = new_id
        self._clock = clock

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        capture = RawCapture(
            id=self._new_id(),
            source=message.source,
            received_at=message.received_at,
            text=message.text,
            media_paths=message.media_paths,
            status=CaptureStatus.PENDING,
        )
        return capture if self._store.add_capture(capture) else None

    def process(self, capture: RawCapture) -> ProcessResult:
        existing = self._store.get_item(capture.item_id)
        if existing is not None:
            return self._resumed(capture, existing)
        if forces_request(capture.text):
            return self._request(capture)
        urls = extract_urls(capture.text)
        first_url = urls[0] if urls else None
        link = None if first_url is None else self._inspector.inspect(first_url)
        try:
            filing = self._filer.file(capture.text, link)
        except LlmDeferred:
            return self._gpu_busy(capture)
        except LlmError as error:
            logger.warning(
                "capture %s deferred: ai_unavailable (%s)", capture.id, type(error).__name__
            )
            return Deferred(capture, "ai_unavailable")
        if filing.route is Route.REQUEST:
            return self._request(capture)
        return self._filed(capture, filing, first_url)

    def handle(self, message: IncomingMessage) -> ProcessResult:
        capture = self.receive(message)
        return Duplicate() if capture is None else self.process(capture)

    def retry_pending(self) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for capture in self._store.pending_captures():
            try:
                results.append(self.process(capture))
            except Exception:
                logger.exception("capture %s failed unexpectedly; left pending", capture.id)
        return results

    def _gpu_busy(self, capture: RawCapture) -> Deferred:
        logger.info("capture %s deferred: gpu_busy", capture.id)
        return Deferred(capture, "gpu_busy")

    def _resumed(self, capture: RawCapture, existing: Item) -> Filed:
        self._store.set_capture_status(capture.id, CaptureStatus.FILED)
        return Filed(existing, unsure=False)

    def _request(self, capture: RawCapture) -> IsRequest:
        self._store.set_capture_status(capture.id, CaptureStatus.REQUEST)
        return IsRequest(capture.with_status(CaptureStatus.REQUEST))

    def _filed(self, capture: RawCapture, filing: Filing, source_url: str | None) -> Filed:
        item = Item.from_filing(capture.item_id, capture, filing, source_url, self._clock())
        self._store.save_item(item)
        self._store.set_capture_status(capture.id, CaptureStatus.FILED)
        return Filed(item, unsure=filing.route is Route.UNSURE)
