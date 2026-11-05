from collections.abc import Callable
from datetime import datetime
from typing import Any

from builders import BASE, a_capture, a_source, an_item, stored_completion
from fakes.memory_store import MemoryStore

from stash.capture import (
    Button,
    CaptureFiler,
    CapturePipeline,
    IncomingMessage,
    IntakeStore,
    Reply,
    Reroute,
)
from stash.domain import CaptureStatus, Item, ItemType, RawCapture, Stage
from stash.enrich.links import LinkInspector

RAMEN_URL = "https://example.com/ramen-tokyo"
SAMPLE_TEXT = "Ramen in Shibuya"
QUESTION = "what can I do Saturday afternoon?"
FORCED_QUESTION = "? what can I do"
LINK_WITH_A_QUERY = "https://x.test/a?b=1"
BARE_QUESTION_MARK = "?"
INDENTED_FORCED_QUESTION = "  ? what can I do"
FORCING_TEXTS = [BARE_QUESTION_MARK, INDENTED_FORCED_QUESTION, "\n?why"]
NON_FORCING_TEXTS = [LINK_WITH_A_QUERY, "what time is it?", ""]
COMPLETED_ITEM_ID = "i1"
COMPLETED_OUTCOME_ID = "o-i1"
COMPLETED_TITLE = "Dune"
INVALID_RATINGS = ["0", "6", "x", "+3"]
INVALID_KEEP_CHOICES = ["2", "yes"]


def a_message(
    text: str = SAMPLE_TEXT,
    message_id: str = "m1",
    media_paths: tuple[str, ...] = (),
    received_at: datetime = BASE,
) -> IncomingMessage:
    return IncomingMessage(
        source=a_source(message_id),
        text=text,
        media_paths=media_paths,
        received_at=received_at,
    )


def received(pipeline: CapturePipeline, text: str) -> RawCapture:
    capture = pipeline.receive(a_message(text))
    if capture is None:
        raise AssertionError(f"the pipeline refused to receive {text!r}")
    return capture


def a_filing_answer(**overrides: Any) -> dict[str, object]:
    answer: dict[str, object] = {
        "route": "capture",
        "item_type": "place",
        "title": "Ichiran ramen",
        "stage": "want_to",
        "details": {"city": "Tokyo"},
        "tags": [],
        "people": [],
        "date": None,
    }
    return {**answer, **overrides}


def a_request_answer(**overrides: Any) -> dict[str, object]:
    return a_filing_answer(route="request", **overrides)


def an_unsure_answer(**overrides: Any) -> dict[str, object]:
    return a_filing_answer(route="unsure", item_type="other", details={}, **overrides)


def a_placed_item(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "id": "i1",
        "capture_id": "c1",
        "item_type": ItemType.PLACE,
        "stage": Stage.WANT_TO,
    }
    return an_item(**{**fields, **overrides})


def sequential_ids() -> Callable[[], str]:
    issued = 0

    def next_id() -> str:
        nonlocal issued
        issued += 1
        return f"{issued:032x}"

    return next_id


def a_pipeline(
    store: IntakeStore,
    inspector: LinkInspector,
    filer: CaptureFiler,
    clock: Callable[[], datetime] = lambda: BASE,
) -> CapturePipeline:
    return CapturePipeline(store, inspector, filer, sequential_ids(), clock)


def store_with_filed_item(
    store: MemoryStore | None = None, **overrides: Any
) -> tuple[MemoryStore, Item]:
    store = store or MemoryStore()
    capture = a_capture(status=CaptureStatus.FILED)
    store.add_capture(capture)
    item = a_placed_item(id=capture.id, capture_id=capture.id, **overrides)
    store.save_item(item)
    return store, item


def button_data(reply: Reply, label: str) -> str:
    return next(button.data for row in reply.buttons for button in row if button.label == label)


def button_labels(rows: tuple[tuple[Button, ...], ...]) -> list[list[str]]:
    return [[button.label for button in row] for row in rows]


def a_store_with_a_completed_item(**item_overrides: Any) -> MemoryStore:
    store = MemoryStore()
    stored_completion(store, COMPLETED_ITEM_ID, title=COMPLETED_TITLE, **item_overrides)
    return store


def text_of(answer: Reply | Reroute) -> str:
    assert isinstance(answer, Reply)
    return answer.text
