from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from stash.config import ProviderName, ProviderSettings
from stash.domain import (
    CaptureStatus,
    Filing,
    Item,
    ItemType,
    RawCapture,
    Route,
    SourceRef,
    Stage,
)

BASE = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
LATER = BASE + timedelta(hours=3)
NAIVE = datetime(2026, 11, 2, 12, 0)
API_KEY = "sk-or-test-key"
PLUS_FIVE = timezone(timedelta(hours=5))
EARLIER_INSTANT_LATER_WALL_CLOCK = BASE.astimezone(PLUS_FIVE) - timedelta(minutes=30)


def chat_body(content: str) -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def minutes_after(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


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
    }
    return Item(**{**fields, **overrides})


def titles(items: list[Item]) -> list[str]:
    return [item.title for item in items]
