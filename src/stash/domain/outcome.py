import datetime as dt
from dataclasses import dataclass, replace

from stash.domain._validation import (
    frozen_strings,
    require_aware,
    require_max_length,
    require_plain_date,
    require_text,
)
from stash.domain.wire import require_wire_safe_id

OUTCOME_NOTES_LIMIT = 4000
MAX_TAKEAWAYS = 20
TAKEAWAY_LIMIT = 500
MIN_RATING = 1
MAX_RATING = 5


def _require_takeaways(takeaways: tuple[str, ...]) -> None:
    if len(takeaways) > MAX_TAKEAWAYS:
        raise ValueError(f"takeaways must have at most {MAX_TAKEAWAYS} entries")
    for takeaway in takeaways:
        require_text("takeaway", takeaway)
        require_max_length("takeaway", takeaway, TAKEAWAY_LIMIT)


@dataclass(frozen=True, slots=True)
class Outcome:
    id: str
    item_id: str
    completed_on: dt.date
    rating: int | None
    notes: str
    takeaways: tuple[str, ...]
    recorded_at: dt.datetime
    edited_at: dt.datetime | None = None

    def __post_init__(self) -> None:
        require_wire_safe_id("outcome id", self.id)
        require_wire_safe_id("outcome item id", self.item_id)
        require_plain_date("completed_on", self.completed_on)
        require_aware("recorded_at", self.recorded_at)
        if self.edited_at is not None:
            require_aware("edited_at", self.edited_at)
        if self.rating is not None and not MIN_RATING <= self.rating <= MAX_RATING:
            raise ValueError(f"rating must be between {MIN_RATING} and {MAX_RATING}")
        require_max_length("notes", self.notes, OUTCOME_NOTES_LIMIT)
        object.__setattr__(self, "takeaways", frozen_strings("takeaways", self.takeaways))
        _require_takeaways(self.takeaways)

    def with_notes(self, notes: str, takeaways: tuple[str, ...], now: dt.datetime) -> "Outcome":
        return replace(self, notes=notes, takeaways=takeaways, edited_at=now)

    def with_rating(self, rating: int, now: dt.datetime) -> "Outcome":
        return replace(self, rating=rating, edited_at=now)
