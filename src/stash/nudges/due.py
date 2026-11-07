import datetime as dt
from dataclasses import dataclass

from stash.domain import Item, KeyDate, Nudge, NudgeKind, Person, Step, require_aware
from stash.nudges.digest import EMPTY_SECTIONS, DigestSections
from stash.nudges.person_key_dates import require_key_date_of

DIGEST_SUBJECT = "weekly"
DIGEST_TITLE = "Weekly digest"


@dataclass(frozen=True, slots=True)
class StepReminder:
    step: Step
    item: Item
    due_at: dt.datetime

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)
        if self.step.item_id != self.item.id:
            raise ValueError(f"step {self.step.id!r} belongs to item {self.step.item_id!r}")

    @property
    def nudge(self) -> Nudge:
        return Nudge(NudgeKind.STEP, self.step.id, self.due_at, self.step.text)


@dataclass(frozen=True, slots=True)
class DateReminder:
    item: Item
    on: dt.date
    due_at: dt.datetime

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)
        if self.on != self.item.date:
            raise ValueError(f"{self.on} is not the item date of {self.item.id!r}")

    @property
    def nudge(self) -> Nudge:
        return Nudge(NudgeKind.ITEM_DATE, self.item.id, self.due_at, self.item.title)


@dataclass(frozen=True, slots=True)
class FollowUp:
    item: Item
    due_at: dt.datetime

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)

    @property
    def nudge(self) -> Nudge:
        return Nudge(NudgeKind.FOLLOWUP, self.item.id, self.due_at, self.item.title)


@dataclass(frozen=True, slots=True)
class StuckItem:
    item: Item
    due_at: dt.datetime

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)

    @property
    def nudge(self) -> Nudge:
        return Nudge(NudgeKind.STUCK, self.item.id, self.due_at, self.item.title)


@dataclass(frozen=True, slots=True)
class WeeklyDigest:
    due_at: dt.datetime
    stuck: tuple[StuckItem, ...]
    sections: DigestSections = EMPTY_SECTIONS

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)
        if any(stuck.due_at != self.due_at for stuck in self.stuck):
            raise ValueError("stuck items ride the digest at the same instant")

    @property
    def nudge(self) -> Nudge:
        return Nudge(NudgeKind.DIGEST, DIGEST_SUBJECT, self.due_at, DIGEST_TITLE)

    @property
    def nudges(self) -> tuple[Nudge, ...]:
        return (*(stuck.nudge for stuck in self.stuck), *self._forgotten_nudges, self.nudge)

    @property
    def _forgotten_nudges(self) -> tuple[Nudge, ...]:
        return tuple(
            Nudge(NudgeKind.FORGOTTEN, item.id, self.due_at, item.title)
            for item in self.sections.forgotten
        )


@dataclass(frozen=True, slots=True)
class PersonDateReminder:
    person: Person
    key_date: KeyDate
    on: dt.date
    lead: int
    days_left: int
    gift_ideas: tuple[str, ...]
    due_at: dt.datetime

    def __post_init__(self) -> None:
        require_aware("due_at", self.due_at)
        require_key_date_of(self.person, self.key_date)
        if self.lead < 0:
            raise ValueError("lead must be >= 0")
        if self.days_left < 0:
            raise ValueError("days_left must be >= 0")

    @property
    def nudge(self) -> Nudge:
        subject = f"{self.key_date.id}@{self.on.isoformat()}#{self.lead}"
        return Nudge(NudgeKind.PERSON_DATE, subject, self.due_at, self.person.name)


DueNudge = StepReminder | DateReminder | FollowUp | PersonDateReminder | WeeklyDigest
