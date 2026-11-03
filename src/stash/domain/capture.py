from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from stash.domain._validation import require_aware
from stash.domain.media import safe_media_paths
from stash.domain.wire import require_wire_safe_id


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

    def with_status(self, status: CaptureStatus) -> "RawCapture":
        return replace(self, status=status)
