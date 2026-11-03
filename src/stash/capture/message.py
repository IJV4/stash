from dataclasses import dataclass
from datetime import datetime

from stash.domain import SourceRef, require_aware
from stash.domain.media import safe_media_paths


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    source: SourceRef
    text: str
    media_paths: tuple[str, ...]
    received_at: datetime

    def __post_init__(self) -> None:
        require_aware("received_at", self.received_at)
        object.__setattr__(self, "media_paths", safe_media_paths("media_paths", self.media_paths))
