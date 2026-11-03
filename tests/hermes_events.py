from collections.abc import Sequence
from dataclasses import dataclass

OWNER_ID = "42"
STRANGER_ID = "99"


@dataclass(frozen=True, slots=True)
class FakeSource:
    chat_id: str
    user_id: str | None


@dataclass(frozen=True, slots=True)
class FakeEvent:
    text: str | None
    source: FakeSource
    message_id: str | None
    media_urls: Sequence[str] | None
    internal: bool = False


def an_event(
    text: str | None = "Ramen in Shibuya",
    user_id: str | None = OWNER_ID,
    chat_id: str = OWNER_ID,
    message_id: str | None = "m1",
    media_urls: Sequence[str] | None = None,
    internal: bool = False,
) -> FakeEvent:
    return FakeEvent(text, FakeSource(chat_id, user_id), message_id, media_urls, internal)
