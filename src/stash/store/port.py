from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from stash.domain import (
    CaptureStatus,
    Item,
    ItemType,
    KeyDate,
    Nudge,
    NudgeKey,
    NudgeKind,
    Outcome,
    Person,
    RawCapture,
    Stage,
    Step,
    require_aware,
)

DEFAULT_PAGE_SIZE = 20
RANGE_ORDER_MESSAGE = "start must not be after end"
BACKUP_LAST_SUCCESS_KEY = "backup.last_success"


class UnknownCaptureError(Exception):
    pass


class UnknownItemError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(item_id)
        self.item_id = item_id


class StaleItemError(Exception):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"item {item_id!r} changed after it was read")
        self.item_id = item_id


class ParentIsGroupedError(Exception):
    def __init__(self, parent_id: str) -> None:
        super().__init__(f"item {parent_id!r} is in a group, so nothing can be grouped under it")
        self.item_id = parent_id


class ChildHoldsItemsError(Exception):
    def __init__(self, child_id: str) -> None:
        super().__init__(f"item {child_id!r} holds items, so it cannot be grouped")
        self.item_id = child_id


class DuplicateOutcomeError(ValueError):
    def __init__(self, outcome_id: str) -> None:
        super().__init__(f"outcome id {outcome_id!r} already exists")


class DuplicateStepError(ValueError):
    def __init__(self, step_id: str) -> None:
        super().__init__(f"step id {step_id!r} already belongs to another item")


class DuplicateNameError(ValueError):
    def __init__(self, person: Person, other: Person) -> None:
        super().__init__(f"{person.name!r} shares a name or alias with {other.name!r}")


class UnknownPersonError(Exception):
    def __init__(self, person_id: str) -> None:
        super().__init__(person_id)
        self.person_id = person_id


def require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def require_date_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError(RANGE_ORDER_MESSAGE)


def require_instant_range(start: datetime, end: datetime) -> None:
    require_aware("start", start)
    require_aware("end", end)
    if start > end:
        raise ValueError(RANGE_ORDER_MESSAGE)


def require_same_item(item: Item, replacing: Item) -> None:
    if item.id != replacing.id:
        raise ValueError(f"item {item.id!r} cannot replace item {replacing.id!r}")


def require_parent(child: Item) -> str:
    if child.parent_id is None:
        raise ValueError(f"item {child.id!r} has no parent to be grouped under")
    return child.parent_id


def require_outcome_for_item(item: Item, outcome: Outcome) -> None:
    if outcome.item_id != item.id:
        raise ValueError(f"outcome {outcome.id!r} is for item {outcome.item_id!r}, not {item.id!r}")


def require_steps_for_item(item_id: str, steps: Sequence[Step]) -> None:
    seen: set[str] = set()
    for step in steps:
        if step.item_id != item_id:
            raise ValueError(f"step {step.id!r} is for item {step.item_id!r}, not {item_id!r}")
        if step.id in seen:
            raise ValueError(f"step id {step.id!r} is repeated")
        seen.add(step.id)


def require_distinct_names(person: Person, others: Sequence[Person]) -> None:
    for other in others:
        if other.id != person.id and person.shares_a_name_with(other):
            raise DuplicateNameError(person, other)


def find_named(people: Sequence[Person], name: str) -> Person | None:
    return next((person for person in people if person.answers_to(name)), None)


class CaptureStore(Protocol):
    def add_capture(self, capture: RawCapture) -> bool: ...

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None: ...

    def get_capture(self, capture_id: str) -> RawCapture | None: ...

    def pending_captures(self) -> list[RawCapture]: ...


class ItemStore(Protocol):
    def save_item(self, item: Item) -> None: ...

    def update_item(self, item: Item, *, replacing: Item) -> None: ...

    def group_item(self, child: Item, *, replacing: Item) -> None: ...

    def get_item(self, item_id: str) -> Item | None: ...

    def delete_item_if_untouched(self, item_id: str) -> bool: ...

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]: ...

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]: ...

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]: ...

    def children_of(self, parent_id: str) -> list[Item]: ...

    def done_between(self, start: date, end: date) -> list[Item]: ...

    def items_dated_between(self, start: date, end: date) -> list[Item]: ...

    def planned_awaiting_outcome_dated_between(self, start: date, end: date) -> list[Item]: ...

    def want_to_older_than(self, cutoff: datetime, limit: int) -> list[Item]: ...

    def doing_older_than(self, cutoff: datetime, limit: int) -> list[Item]: ...

    def created_between(self, start: datetime, end: datetime) -> list[Item]: ...


class OutcomeStore(Protocol):
    def add_outcome(self, outcome: Outcome) -> None: ...

    def save_outcome(self, outcome: Outcome) -> None: ...

    def record_completion(self, item: Item, outcome: Outcome, *, replacing: Item) -> None: ...

    def outcomes_for(self, item_id: str) -> list[Outcome]: ...

    def get_outcome(self, outcome_id: str) -> Outcome | None: ...


class StepStore(Protocol):
    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None: ...

    def steps_for(self, item_id: str) -> list[Step]: ...

    def save_step(self, step: Step) -> None: ...

    def get_step(self, step_id: str) -> Step | None: ...

    def open_confirmed_steps(self) -> list[Step]: ...


class PeopleStore(Protocol):
    def save_person(self, person: Person) -> None: ...

    def get_person(self, person_id: str) -> Person | None: ...

    def delete_person(self, person_id: str) -> None: ...

    def list_people(self) -> list[Person]: ...

    def find_by_name(self, name: str) -> Person | None: ...

    def save_key_date(self, key_date: KeyDate) -> None: ...

    def delete_key_date(self, key_date_id: str) -> None: ...

    def key_dates_for(self, person_id: str) -> list[KeyDate]: ...

    def key_dates_between(self, start: date, end: date) -> list[tuple[KeyDate, date]]: ...

    def link(self, item_id: str, person_id: str) -> None: ...

    def unlink(self, item_id: str, person_id: str) -> None: ...

    def people_for(self, item_id: str) -> list[Person]: ...

    def items_for(self, person_id: str, item_type: ItemType | None = None) -> list[Item]: ...

    def items_naming_people(self) -> list[Item]: ...


class NudgeLedger(Protocol):
    def was_sent(self, key: NudgeKey) -> bool: ...

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool: ...

    def last_sent(self, kind: NudgeKind) -> datetime | None: ...


class SettingsStore(Protocol):
    def get_setting(self, key: str) -> str | None: ...

    def put_setting(self, key: str, value: str) -> None: ...


class Store(
    CaptureStore,
    ItemStore,
    OutcomeStore,
    StepStore,
    PeopleStore,
    NudgeLedger,
    SettingsStore,
    Protocol,
): ...


class StoreBusyError(Exception):
    pass


class BackupError(Exception):
    pass


class BackupSource(Protocol):
    def backup_to(self, target: Path) -> None: ...


class BackupWriter(Protocol):
    def write(self, directory: Path, today: date) -> Path: ...


class Closeable(Protocol):
    def close(self) -> None: ...
