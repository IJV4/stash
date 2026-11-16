import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from stash.capture.message import IncomingMessage
from stash.capture.ports import CaptureFiler, ItemLinker, MediaKeeper
from stash.capture.results import (
    DeferralReason,
    Deferred,
    Duplicate,
    Filed,
    IsRequest,
    ProcessResult,
)
from stash.capture.routing import is_forced_request
from stash.domain import CaptureStatus, Filing, Item, RawCapture, Route
from stash.domain.media import safe_media_paths
from stash.enrich.links import LinkInspector
from stash.enrich.urls import extract_urls
from stash.llm.errors import LlmDeferred, LlmError
from stash.store.port import Store

logger = logging.getLogger(__name__)

NOT_AN_AGENT_CAPTURE = "only a capture from the agent can be processed as an agent capture"


@dataclass(frozen=True, slots=True)
class _Classified:
    filing: Filing
    source_url: str | None

    def without_request(self) -> "_Classified":
        return replace(self, filing=self.filing.without_request())


class CapturePipeline:
    def __init__(
        self,
        store: Store,
        inspector: LinkInspector,
        filer: CaptureFiler,
        new_id: Callable[[], str],
        clock: Callable[[], datetime],
        linker: ItemLinker,
        keeper: MediaKeeper | None = None,
    ) -> None:
        self._store = store
        self._inspector = inspector
        self._filer = filer
        self._new_id = new_id
        self._clock = clock
        self._linker = linker
        self._keeper = keeper

    def receive(self, message: IncomingMessage) -> RawCapture | None:
        capture_id = self._new_id()
        capture = RawCapture(
            id=capture_id,
            source=message.source,
            received_at=message.received_at,
            text=message.text,
            media_paths=self._owned(capture_id, message.media_paths),
            status=CaptureStatus.PENDING,
        )
        try:
            added = self._store.add_capture(capture)
        except BaseException:
            self._discard_copies(capture, message)
            raise
        if not added:
            self._discard_copies(capture, message)
            return None
        return capture

    def _discard_copies(self, capture: RawCapture, message: IncomingMessage) -> None:
        if self._keeper is None:
            return
        copies = [path for path in capture.media_paths if path not in message.media_paths]
        if copies:
            self._keeper.discard(copies)

    def _owned(self, capture_id: str, paths: tuple[str, ...]) -> tuple[str, ...]:
        if self._keeper is None or not paths:
            return paths
        try:
            return safe_media_paths("media_paths", self._keeper.keep(capture_id, paths))
        except Exception:
            logger.exception(
                "capture %s: keeping media failed; the original paths stay", capture_id
            )
            return paths

    def process(self, capture: RawCapture) -> ProcessResult:
        if capture.source.is_agent:
            return self.process_agent(capture)
        existing = self._store.get_item(capture.item_id)
        if existing is not None:
            return self._resumed(capture, existing)
        if is_forced_request(capture):
            return self._request(capture)
        classified = self._classified(capture)
        if isinstance(classified, Deferred):
            return classified
        if classified.filing.route is Route.REQUEST:
            return self._request(capture)
        return self._filed(capture, classified)

    def process_agent(self, capture: RawCapture) -> Filed | Deferred:
        if not capture.source.is_agent:
            raise ValueError(NOT_AN_AGENT_CAPTURE)
        existing = self._store.get_item(capture.item_id)
        if existing is not None:
            return self._resumed(capture, existing)
        classified = self._classified(capture)
        if isinstance(classified, Deferred):
            return classified
        return self._filed(capture, classified.without_request())

    def handle(self, message: IncomingMessage) -> ProcessResult:
        capture = self.receive(message)
        return Duplicate() if capture is None else self.process(capture)

    def retry_pending(self, limit: int | None = None) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for capture in self._store.pending_captures()[:limit]:
            try:
                results.append(self.process(capture))
            except Exception:
                logger.exception("capture %s failed unexpectedly; left pending", capture.id)
        return results

    def _classified(self, capture: RawCapture) -> _Classified | Deferred:
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
            return Deferred(capture, DeferralReason.AI_UNAVAILABLE)
        facts = {} if link is None else link.facts()
        return _Classified(filing.with_facts(facts), first_url)

    def _gpu_busy(self, capture: RawCapture) -> Deferred:
        logger.info("capture %s deferred: gpu_busy", capture.id)
        return Deferred(capture, DeferralReason.GPU_BUSY)

    def _resumed(self, capture: RawCapture, existing: Item) -> Filed:
        self._store.set_capture_status(capture.id, CaptureStatus.FILED)
        return Filed(existing, unsure=False)

    def _request(self, capture: RawCapture) -> IsRequest:
        self._store.set_capture_status(capture.id, CaptureStatus.REQUEST)
        return IsRequest(capture.with_status(CaptureStatus.REQUEST))

    def _filed(self, capture: RawCapture, classified: _Classified) -> Filed:
        filing = classified.filing
        item = Item.from_filing(
            capture.item_id, capture, filing, classified.source_url, self._clock()
        )
        self._store.save_item(item)
        self._link(item)
        self._store.set_capture_status(capture.id, CaptureStatus.FILED)
        return Filed(item, unsure=filing.route is Route.UNSURE)

    def _link(self, item: Item) -> None:
        try:
            self._linker.link(item)
        except Exception:
            logger.exception("linking people to item %s failed; the item stays filed", item.id)
