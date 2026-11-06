from dataclasses import dataclass

from stash.domain._validation import require_max_length, require_text
from stash.domain.item import Item

SUGGESTION_REASON_LIMIT = 200


def require_reason(reason: str) -> None:
    require_text("reason", reason)
    require_max_length("reason", reason, SUGGESTION_REASON_LIMIT)


@dataclass(frozen=True, slots=True)
class Pick:
    item: Item
    reason: str

    def __post_init__(self) -> None:
        require_reason(self.reason)
