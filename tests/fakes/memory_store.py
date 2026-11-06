import threading
from dataclasses import replace
from datetime import date, datetime
from typing import NamedTuple

from stash.domain import CaptureStatus, Item, ItemType, Outcome, RawCapture, SourceRef, Stage
from stash.store.port import (
    DEFAULT_PAGE_SIZE,
    DuplicateOutcomeError,
    UnknownCaptureError,
    UnknownItemError,
    require_date_range,
    require_non_negative,
    require_outcome_for_item,
)


class Recency(NamedTuple):
    completed_on: date
    recorded_at: datetime
    outcome_id: str


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._captures: dict[str, RawCapture] = {}
        self._sources: set[SourceRef] = set()
        self._items: dict[str, Item] = {}
        self._outcomes: dict[str, Outcome] = {}
        self._settings: dict[str, str] = {}

    def add_capture(self, capture: RawCapture) -> bool:
        with self._lock:
            if capture.source in self._sources:
                return False
            if capture.id in self._captures:
                raise ValueError(f"capture id {capture.id!r} already exists")
            self._captures[capture.id] = capture
            self._sources.add(capture.source)
            return True

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None:
        with self._lock:
            self._captures[capture_id] = self._known_capture(capture_id).with_status(status)

    def get_capture(self, capture_id: str) -> RawCapture | None:
        with self._lock:
            return self._captures.get(capture_id)

    def stored_captures(self) -> list[RawCapture]:
        with self._lock:
            return list(self._captures.values())

    def pending_captures(self) -> list[RawCapture]:
        with self._lock:
            pending = [
                capture
                for capture in self._captures.values()
                if capture.status is CaptureStatus.PENDING
            ]
        return sorted(pending, key=lambda capture: (capture.received_at, capture.id))

    def save_item(self, item: Item) -> None:
        with self._lock:
            self._require_references(item)
            self._items[item.id] = item

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._items.pop(item_id, None)
            self._ungroup_children_of(item_id)
            self._drop_outcomes_of(item_id)

    def delete_item_if_untouched(self, item_id: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.is_done or item.kept or self._has_history(item_id):
                return False
            self.delete_item(item_id)
            return True

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        require_non_negative("limit", limit)
        require_non_negative("offset", offset)
        matching = [
            item
            for item in self._newest_first()
            if (stage is None or item.stage is stage)
            and (item_type is None or item.item_type is item_type)
        ]
        return matching[offset : offset + limit]

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        require_non_negative("limit", limit)
        if not query.strip():
            return []
        needle = query.casefold()
        matching = [item for item in self._newest_first() if _mentions(item, needle)]
        return matching[:limit]

    def add_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            self._require_stored_item(outcome.item_id)
            self._require_unused_outcome_id(outcome)
            self._outcomes[outcome.id] = outcome

    def save_outcome(self, outcome: Outcome) -> None:
        with self._lock:
            self._require_stored_item(outcome.item_id)
            self._outcomes[outcome.id] = outcome

    def record_completion(self, item: Item, outcome: Outcome) -> None:
        require_outcome_for_item(item, outcome)
        with self._lock:
            self._require_stored_item(item.id)
            self._require_references(item)
            self._require_unused_outcome_id(outcome)
            self._items[item.id] = item
            self._outcomes[outcome.id] = outcome

    def outcomes_for(self, item_id: str) -> list[Outcome]:
        with self._lock:
            outcomes = [
                outcome for outcome in self._outcomes.values() if outcome.item_id == item_id
            ]
        return sorted(outcomes, key=_recency)

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        with self._lock:
            return self._outcomes.get(outcome_id)

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        require_non_negative("limit", limit)
        require_non_negative("offset", offset)
        with self._lock:
            kept = [
                item
                for item in self._newest_first()
                if item.in_library and (item_type is None or item.item_type is item_type)
            ]
            latest = self._latest_completions()
        completed = sorted(
            (item for item in kept if item.id in latest),
            key=lambda item: latest[item.id],
            reverse=True,
        )
        never_completed = [item for item in kept if item.id not in latest]
        return (completed + never_completed)[offset : offset + limit]

    def children_of(self, parent_id: str) -> list[Item]:
        with self._lock:
            children = [item for item in self._items.values() if item.parent_id == parent_id]
        return sorted(children, key=lambda item: (item.created_at, item.id))

    def done_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        with self._lock:
            latest = self._latest_completions(start, end)
            ranked = sorted(
                latest,
                key=lambda item_id: (
                    latest[item_id].completed_on,
                    latest[item_id].recorded_at,
                    item_id,
                ),
                reverse=True,
            )
            return [self._items[item_id] for item_id in ranked]

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            return self._settings.get(key)

    def put_setting(self, key: str, value: str) -> None:
        with self._lock:
            self._settings[key] = value

    def _known_capture(self, capture_id: str) -> RawCapture:
        capture = self._captures.get(capture_id)
        if capture is None:
            raise UnknownCaptureError(capture_id)
        return capture

    def _latest_completions(
        self, start: date | None = None, end: date | None = None
    ) -> dict[str, Recency]:
        latest: dict[str, Recency] = {}
        with self._lock:
            for outcome in self._outcomes.values():
                if _within(outcome.completed_on, start, end):
                    rank = _recency(outcome)
                    latest[outcome.item_id] = max(rank, latest.get(outcome.item_id, rank))
        return latest

    def _ungroup_children_of(self, parent_id: str) -> None:
        for child in [item for item in self._items.values() if item.parent_id == parent_id]:
            self._items[child.id] = replace(child, parent_id=None)

    def _has_history(self, item_id: str) -> bool:
        return any(outcome.item_id == item_id for outcome in self._outcomes.values()) or any(
            item.parent_id == item_id for item in self._items.values()
        )

    def _drop_outcomes_of(self, item_id: str) -> None:
        self._outcomes = {
            outcome_id: outcome
            for outcome_id, outcome in self._outcomes.items()
            if outcome.item_id != item_id
        }

    def _require_stored_item(self, item_id: str) -> None:
        if item_id not in self._items:
            raise UnknownItemError(item_id)

    def _require_unused_outcome_id(self, outcome: Outcome) -> None:
        if outcome.id in self._outcomes:
            raise DuplicateOutcomeError(outcome.id)

    def _require_references(self, item: Item) -> None:
        self._known_capture(item.capture_id)
        if item.parent_id is not None and item.parent_id not in self._items:
            raise UnknownItemError(item.parent_id)

    def _newest_first(self) -> list[Item]:
        with self._lock:
            items = list(self._items.values())
        return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)


def _recency(outcome: Outcome) -> Recency:
    return Recency(outcome.completed_on, outcome.recorded_at, outcome.id)


def _within(day: date, start: date | None, end: date | None) -> bool:
    return (start is None or start <= day) and (end is None or day <= end)


def _mentions(item: Item, needle: str) -> bool:
    return any(needle in text.casefold() for text in (item.title, item.note, *item.tags))
