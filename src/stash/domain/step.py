import datetime as dt
from dataclasses import dataclass, replace

from stash.domain._validation import (
    require_aware,
    require_max_length,
    require_plain_date,
    require_text,
)
from stash.domain.wire import require_wire_safe_id

STEP_TEXT_LIMIT = 200
MIN_LEAD_DAYS = 0
MAX_LEAD_DAYS = 60
MIN_POSITION = 0
EXACTLY_ONE_DUE = "a step needs exactly one of lead_days and due_on"
NOTHING_TO_EDIT = "give a text, a lead time or a date"


def _require_exactly_one_due(lead_days: int | None, due_on: dt.date | None) -> None:
    if (lead_days is None) == (due_on is None):
        raise ValueError(EXACTLY_ONE_DUE)


def _require_lead_days_in_range(lead_days: int | None) -> None:
    if lead_days is not None and not MIN_LEAD_DAYS <= lead_days <= MAX_LEAD_DAYS:
        raise ValueError(f"lead_days must be between {MIN_LEAD_DAYS} and {MAX_LEAD_DAYS}")


@dataclass(frozen=True, slots=True)
class Step:
    id: str
    item_id: str
    text: str
    lead_days: int | None
    due_on: dt.date | None
    confirmed: bool
    done: bool
    position: int
    created_at: dt.datetime

    def __post_init__(self) -> None:
        require_wire_safe_id("step id", self.id)
        require_wire_safe_id("step item id", self.item_id)
        require_text("text", self.text)
        require_max_length("text", self.text, STEP_TEXT_LIMIT)
        _require_exactly_one_due(self.lead_days, self.due_on)
        _require_lead_days_in_range(self.lead_days)
        if self.due_on is not None:
            require_plain_date("due_on", self.due_on)
        if self.position < MIN_POSITION:
            raise ValueError("position must not be negative")
        require_aware("created_at", self.created_at)

    def due_date(self, item_date: dt.date | None) -> dt.date | None:
        if self.lead_days is None:
            return self.due_on
        if item_date is None:
            return None
        return item_date - dt.timedelta(days=self.lead_days)

    def confirmed_now(self) -> "Step":
        return replace(self, confirmed=True)

    def marked_done(self) -> "Step":
        return replace(self, done=True)

    def edited(
        self,
        *,
        text: str | None = None,
        lead_days: int | None = None,
        due_on: dt.date | None = None,
    ) -> "Step":
        if text is None and lead_days is None and due_on is None:
            raise ValueError(NOTHING_TO_EDIT)
        if lead_days is None and due_on is None:
            lead_days, due_on = self.lead_days, self.due_on
        return replace(
            self,
            text=self.text if text is None else text,
            lead_days=lead_days,
            due_on=due_on,
        )
