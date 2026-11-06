import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple

from stash.domain._validation import require_aware, require_text
from stash.domain.instant import utc_text
from stash.domain.wire import require_wire_safe_id


class NudgeKey(NamedTuple):
    kind: str
    subject_id: str
    due_at: str


class NudgeKind(StrEnum):
    STEP = "step"
    ITEM_DATE = "item_date"
    FOLLOWUP = "followup"
    DIGEST = "digest"
    STUCK = "stuck"


@dataclass(frozen=True, slots=True)
class Nudge:
    kind: NudgeKind
    subject_id: str
    due_at: dt.datetime
    title: str

    def __post_init__(self) -> None:
        require_wire_safe_id("nudge subject id", self.subject_id)
        require_aware("due_at", self.due_at)
        require_text("title", self.title)

    @property
    def key(self) -> NudgeKey:
        return NudgeKey(self.kind.value, self.subject_id, utc_text(self.due_at))
