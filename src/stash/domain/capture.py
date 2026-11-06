from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from stash.domain._validation import require_aware
from stash.domain.media import safe_media_paths
from stash.domain.wire import require_wire_safe_id

AGENT_CHAT_ID = "agent"


class Route(StrEnum):
    CAPTURE = "capture"
    REQUEST = "request"
    UNSURE = "unsure"


class CaptureStatus(StrEnum):
    PENDING = "pending"
    FILED = "filed"
    REQUEST = "request"


@dataclass(frozen=True, slots=True)
class SourceRef:
    chat_id: str
    message_id: str

    @classmethod
    def agent(cls, message_id: str) -> "SourceRef":
        return cls(chat_id=AGENT_CHAT_ID, message_id=message_id)

    @staticmethod
    def is_agent_chat(chat_id: str) -> bool:
        return chat_id == AGENT_CHAT_ID

    @property
    def is_agent(self) -> bool:
        return self.is_agent_chat(self.chat_id)


@dataclass(frozen=True, slots=True)
class RawCapture:
    id: str
    source: SourceRef
    received_at: datetime
    text: str
    media_paths: tuple[str, ...]
    status: CaptureStatus

    def __post_init__(self) -> None:
        require_wire_safe_id("capture id", self.id)
        require_aware("received_at", self.received_at)
        object.__setattr__(self, "media_paths", safe_media_paths("media_paths", self.media_paths))

    @property
    def item_id(self) -> str:
        return self.id

    @property
    def may_be_a_request(self) -> bool:
        return not self.source.is_agent

    def with_status(self, status: CaptureStatus) -> "RawCapture":
        return replace(self, status=status)
