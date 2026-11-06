from dataclasses import dataclass

from stash.domain import Pick, require_reason
from stash.domain.wire import require_wire_safe_id

CONTEXT_LIMIT = 500
SUGGESTION_LIMIT = 3


class ContextTooLong(ValueError):
    def __init__(self) -> None:
        super().__init__(f"context must be at most {CONTEXT_LIMIT} characters")


@dataclass(frozen=True, slots=True)
class Suggestion:
    item_id: str
    reason: str

    def __post_init__(self) -> None:
        require_wire_safe_id("item id", self.item_id)
        require_reason(self.reason)


@dataclass(frozen=True, slots=True)
class Picked:
    picks: tuple[Pick, ...]


@dataclass(frozen=True, slots=True)
class Unavailable:
    pass
