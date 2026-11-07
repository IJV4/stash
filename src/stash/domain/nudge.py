import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple, Self

from stash.domain._validation import require_aware, require_text
from stash.domain.instant import utc_text
from stash.domain.wire import MAX_ID_LENGTH, require_wire_safe_id

OCCURRENCE_AND_LEAD_LENGTH = len("@2027-03-06#365")
MAX_NUDGE_SUBJECT_LENGTH = MAX_ID_LENGTH + OCCURRENCE_AND_LEAD_LENGTH


class NudgeKind(StrEnum):
    STEP = "step"
    ITEM_DATE = "item_date"
    FOLLOWUP = "followup"
    DIGEST = "digest"
    STUCK = "stuck"
    FORGOTTEN = "forgotten"
    PERSON_DATE = "person_date"


class NudgeKey(NamedTuple):
    kind: str
    subject_id: str
    due_at: str

    @classmethod
    def of(cls, kind: NudgeKind, subject_id: str, at: dt.datetime) -> Self:
        return cls(kind.value, subject_id, utc_text(at))


@dataclass(frozen=True, slots=True)
class Nudge:
    kind: NudgeKind
    subject_id: str
    due_at: dt.datetime
    title: str

    def __post_init__(self) -> None:
        require_wire_safe_id("nudge subject id", self.subject_id, MAX_NUDGE_SUBJECT_LENGTH)
        require_aware("due_at", self.due_at)
        require_text("title", self.title)

    @property
    def key(self) -> NudgeKey:
        return NudgeKey.of(self.kind, self.subject_id, self.due_at)
