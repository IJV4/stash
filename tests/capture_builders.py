from collections.abc import Callable
from datetime import datetime
from typing import Any

from builders import BASE, a_capture, a_source, an_item
from fakes.memory_store import MemoryStore

from stash.capture import CaptureFiler, CapturePipeline, IncomingMessage, IntakeStore, Reply
from stash.domain import CaptureStatus, Item, ItemType, Stage
from stash.enrich.links import LinkInspector

RAMEN_URL = "https://example.com/ramen-tokyo"


def a_message(
    text: str = "Ramen in Shibuya",
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
