from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from stash.domain._validation import frozen_strings, require_aware


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
        require_aware("received_at", self.received_at)
        object.__setattr__(self, "media_paths", frozen_strings("media_paths", self.media_paths))

    def with_status(self, status: CaptureStatus) -> "RawCapture":
        return replace(self, status=status)
