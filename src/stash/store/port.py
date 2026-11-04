from datetime import date
from pathlib import Path
from typing import Protocol

from stash.domain import CaptureStatus, Item, ItemType, Outcome, RawCapture, Stage

DEFAULT_PAGE_SIZE = 20


class UnknownCaptureError(Exception):
    pass


class UnknownItemError(Exception):
    pass


class DuplicateOutcomeError(ValueError):
    def __init__(self, outcome_id: str) -> None:
        super().__init__(f"outcome id {outcome_id!r} already exists")


def require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def require_date_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError("start must not be after end")


def require_outcome_for_item(item: Item, outcome: Outcome) -> None:
    if outcome.item_id != item.id:
        raise ValueError(f"outcome {outcome.id!r} is for item {outcome.item_id!r}, not {item.id!r}")


class CaptureStore(Protocol):
    def add_capture(self, capture: RawCapture) -> bool: ...

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None: ...

    def get_capture(self, capture_id: str) -> RawCapture | None: ...

    def pending_captures(self) -> list[RawCapture]: ...


class ItemStore(Protocol):
    def save_item(self, item: Item) -> None: ...

    def get_item(self, item_id: str) -> Item | None: ...

    def delete_item(self, item_id: str) -> None: ...

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


class OutcomeStore(Protocol):
    def add_outcome(self, outcome: Outcome) -> None: ...

    def save_outcome(self, outcome: Outcome) -> None: ...

    def record_completion(self, item: Item, outcome: Outcome) -> None: ...

    def outcomes_for(self, item_id: str) -> list[Outcome]: ...

    def get_outcome(self, outcome_id: str) -> Outcome | None: ...


class SettingsStore(Protocol):
    def get_setting(self, key: str) -> str | None: ...

    def put_setting(self, key: str, value: str) -> None: ...


class Store(CaptureStore, ItemStore, OutcomeStore, SettingsStore, Protocol): ...


class BackupError(Exception):
    pass


class BackupSource(Protocol):
    def backup_to(self, target: Path) -> None: ...


class BackupWriter(Protocol):
    def write(self, directory: Path, today: date) -> Path: ...


class Closeable(Protocol):
    def close(self) -> None: ...
