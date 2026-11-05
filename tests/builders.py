from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from stash.config import ProviderName, ProviderSettings
from stash.domain import (
    CaptureStatus,
    Filing,
    Item,
    ItemType,
    Outcome,
    RawCapture,
    Route,
    SourceRef,
    Stage,
)
from stash.store import Store

BASE = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
LATER = BASE + timedelta(hours=3)
NAIVE = datetime(2026, 11, 2, 12, 0)
API_KEY = "sk-or-test-key"
PLUS_FIVE = timezone(timedelta(hours=5))
EARLIER_INSTANT_LATER_WALL_CLOCK = BASE.astimezone(PLUS_FIVE) - timedelta(minutes=30)
PLANNED_FOR = date(2026, 11, 14)
COMPLETED_ON = date(2026, 11, 2)
NON_DONE_STAGES = tuple(stage for stage in Stage if stage is not Stage.DONE)
BARE_STRING_TAKEAWAYS: Any = "Fear"
BARE_STRING_REFUSAL = "separate items"
NONE_TAKEAWAYS: Any = None


def chat_body(content: str) -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def minutes_after(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def days_after(days: int) -> date:
    return COMPLETED_ON + timedelta(days=days)


def a_source(message_id: str = "m1") -> SourceRef:
    return SourceRef(chat_id="chat-1", message_id=message_id)


def a_capture(**overrides: Any) -> RawCapture:
    fields: dict[str, Any] = {
        "id": "c1",
        "source": a_source(),
        "received_at": BASE,
        "text": "Ramen in Shibuya",
        "media_paths": ("media/a.jpg", "media/b.jpg"),
        "status": CaptureStatus.PENDING,
    }
    return RawCapture(**{**fields, **overrides})


def an_ollama_settings(**overrides: Any) -> ProviderSettings:
    fields: dict[str, Any] = {
        "name": ProviderName.OLLAMA,
        "base_url": "http://localhost:11434/v1",
        "model": "llama3:8b",
    }
    return ProviderSettings(**{**fields, **overrides})


def an_openrouter_settings(**overrides: Any) -> ProviderSettings:
    fields: dict[str, Any] = {
        "name": ProviderName.OPENROUTER,
        "base_url": "https://openrouter.ai/api/v1",
        "model": "cloud/model",
        "api_key": API_KEY,
    }
    return ProviderSettings(**{**fields, **overrides})


def a_filing(**overrides: Any) -> Filing:
    fields: dict[str, Any] = {
        "route": Route.CAPTURE,
        "item_type": ItemType.PLACE,
        "title": "Ramen in Shibuya",
        "stage": Stage.WANT_TO,
        "details": {},
        "tags": (),
        "people": (),
        "date": None,
    }
    return Filing(**{**fields, **overrides})


def an_item(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "id": "i1",
        "capture_id": "c1",
        "item_type": ItemType.PLACE,
        "title": "Ramen in Shibuya",
        "stage": Stage.INBOX,
        "source_url": None,
        "note": "",
        "details": {},
        "tags": (),
        "people": (),
        "date": None,
        "created_at": BASE,
        "updated_at": BASE,
        "kept": False,
        "parent_id": None,
        "drop_reason": None,
    }
    return Item(**{**fields, **overrides})


def an_item_at(stage: Stage, **overrides: Any) -> Item:
    date_for_stage = PLANNED_FOR if stage is Stage.PLANNED else None
    return an_item(stage=stage, date=date_for_stage, **overrides)


def an_outcome(**overrides: Any) -> Outcome:
    fields: dict[str, Any] = {
        "id": "o1",
        "item_id": "i1",
        "completed_on": COMPLETED_ON,
        "rating": 4,
        "notes": "Great",
        "takeaways": ("Salt early",),
        "recorded_at": BASE,
        "edited_at": None,
    }
    return Outcome(**{**fields, **overrides})


def titles(items: list[Item]) -> list[str]:
    return [item.title for item in items]


def a_parent_item() -> Item:
    return an_item(id="p1", title="Japan trip")


UNSAFE_WIRE_IDS = ("", "   ", "a:b", "two words", "bell\x07", "x" * 41, "é" * 40)


def stored(store: Store, item: Item) -> Item:
    store.add_capture(a_capture())
    store.save_item(item)
    return item


def stored_item(store: Store, **overrides: Any) -> Item:
    return stored(store, an_item(**overrides))


def fetched_item(store: Store, item_id: str) -> Item:
    item = store.get_item(item_id)
    assert item is not None
    return item


def fetched_outcome(store: Store, outcome_id: str) -> Outcome:
    outcome = store.get_outcome(outcome_id)
    assert outcome is not None
    return outcome


def stored_parent(store: Store) -> Item:
    return stored(store, a_parent_item())


def stored_completion(
    store: Store,
    item_id: str,
    completed_on: date = COMPLETED_ON,
    recorded_at: datetime = BASE,
    **overrides: Any,
) -> Item:
    fields: dict[str, Any] = {"id": item_id, "title": item_id, "stage": Stage.DONE}
    item = stored_item(store, **{**fields, **overrides})
    store.add_outcome(
        an_outcome(
            id=f"o-{item_id}", item_id=item_id, completed_on=completed_on, recorded_at=recorded_at
        )
    )
    return item
