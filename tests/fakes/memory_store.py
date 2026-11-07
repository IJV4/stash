import threading
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime

from fakes.memory_item_writes import MemoryItemWrites
from fakes.memory_ledger import MemoryLedger
from fakes.memory_people import MemoryPeople
from fakes.memory_queries import Recency, mentions, recency_of, within
from fakes.memory_steps import MemorySteps

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
    SourceRef,
    Stage,
    Step,
    require_aware,
)
from stash.store.port import (
    DEFAULT_PAGE_SIZE,
    DuplicateOutcomeError,
    UnknownCaptureError,
    UnknownItemError,
    require_date_range,
    require_instant_range,
    require_non_negative,
    require_outcome_for_item,
    require_steps_for_item,
)


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._captures: dict[str, RawCapture] = {}
        self._sources: set[SourceRef] = set()
        self._items: dict[str, Item] = {}
        self._outcomes: dict[str, Outcome] = {}
        self._writes = MemoryItemWrites(self._lock, self._captures, self._items)
        self._steps = MemorySteps(self._lock)
        self._people = MemoryPeople(self._lock, self._items)
        self._ledger = MemoryLedger(self._lock)
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
        self._writes.save_item(item)

    def update_item(self, item: Item, *, replacing: Item) -> None:
        self._writes.update_item(item, replacing=replacing)

    def group_item(self, child: Item, *, replacing: Item) -> None:
        self._writes.group_item(child, replacing=replacing)

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._items.pop(item_id, None)
            self._ungroup_children_of(item_id)
            self._drop_outcomes_of(item_id)
            self._steps.drop_steps_of(item_id)
            self._people.drop_links_of_item(item_id)

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
        matching = [item for item in self._newest_first() if mentions(item, needle)]
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

    def record_completion(self, item: Item, outcome: Outcome, *, replacing: Item) -> None:
        require_outcome_for_item(item, outcome)
        with self._lock:
            self._writes.require_replaceable(item, replacing)
            self._require_unused_outcome_id(outcome)
            self._writes.put(item)
            self._outcomes[outcome.id] = outcome

    def outcomes_for(self, item_id: str) -> list[Outcome]:
        with self._lock:
            outcomes = [
                outcome for outcome in self._outcomes.values() if outcome.item_id == item_id
            ]
        return sorted(outcomes, key=recency_of)

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

    def items_dated_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        return self._dated_between(start, end)

    def planned_awaiting_outcome_dated_between(self, start: date, end: date) -> list[Item]:
        require_date_range(start, end)
        with self._lock:
            completions = {
                (outcome.item_id, outcome.completed_on) for outcome in self._outcomes.values()
            }
        return [
            item
            for item in self._dated_between(start, end)
            if item.stage is Stage.PLANNED and (item.id, item.date) not in completions
        ]

    def want_to_older_than(self, cutoff: datetime, limit: int) -> list[Item]:
        return self._stage_older_than(Stage.WANT_TO, cutoff, limit)

    def doing_older_than(self, cutoff: datetime, limit: int) -> list[Item]:
        return self._stage_older_than(Stage.DOING, cutoff, limit)

    def created_between(self, start: datetime, end: datetime) -> list[Item]:
        require_instant_range(start, end)
        return [item for item in self._newest_first() if start <= item.created_at < end]

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        require_steps_for_item(item_id, steps)
        with self._lock:
            self._require_stored_item(item_id)
            self._steps.replace_steps(item_id, steps)

    def steps_for(self, item_id: str) -> list[Step]:
        return self._steps.steps_for(item_id)

    def save_step(self, step: Step) -> None:
        with self._lock:
            self._require_stored_item(step.item_id)
            self._steps.save_step(step)

    def get_step(self, step_id: str) -> Step | None:
        return self._steps.get_step(step_id)

    def open_confirmed_steps(self) -> list[Step]:
        return self._steps.open_confirmed_steps()

    def save_person(self, person: Person) -> None:
        self._people.save_person(person)

    def get_person(self, person_id: str) -> Person | None:
        return self._people.get_person(person_id)

    def delete_person(self, person_id: str) -> None:
        self._people.delete_person(person_id)

    def list_people(self) -> list[Person]:
        return self._people.list_people()

    def find_by_name(self, name: str) -> Person | None:
        return self._people.find_by_name(name)

    def save_key_date(self, key_date: KeyDate) -> None:
        self._people.save_key_date(key_date)

    def delete_key_date(self, key_date_id: str) -> None:
        self._people.delete_key_date(key_date_id)

    def key_dates_for(self, person_id: str) -> list[KeyDate]:
        return self._people.key_dates_for(person_id)

    def key_dates_between(self, start: date, end: date) -> list[tuple[KeyDate, date]]:
        return self._people.key_dates_between(start, end)

    def link(self, item_id: str, person_id: str) -> None:
        self._people.link(item_id, person_id)

    def unlink(self, item_id: str, person_id: str) -> None:
        self._people.unlink(item_id, person_id)

    def people_for(self, item_id: str) -> list[Person]:
        return self._people.people_for(item_id)

    def items_for(self, person_id: str, item_type: ItemType | None = None) -> list[Item]:
        return self._people.items_for(person_id, item_type)

    def was_sent(self, key: NudgeKey) -> bool:
        return self._ledger.was_sent(key)

    def record_all_sent(self, nudges: Sequence[Nudge], sent_at: datetime) -> bool:
        return self._ledger.record_all_sent(nudges, sent_at)

    def last_sent(self, kind: NudgeKind) -> datetime | None:
        return self._ledger.last_sent(kind)

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
                if within(outcome.completed_on, start, end):
                    rank = recency_of(outcome)
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

    def _dated_between(self, start: date, end: date) -> list[Item]:
        with self._lock:
            items = list(self._items.values())
        dated = [item for item in items if item.date is not None and start <= item.date <= end]
        return sorted(dated, key=lambda item: (item.date, item.created_at, item.id))

    def _stage_older_than(self, stage: Stage, cutoff: datetime, limit: int) -> list[Item]:
        require_aware("cutoff", cutoff)
        require_non_negative("limit", limit)
        with self._lock:
            items = list(self._items.values())
        stale = [item for item in items if item.stage is stage and item.updated_at < cutoff]
        return sorted(stale, key=lambda item: (item.updated_at, item.id))[:limit]

    def _newest_first(self) -> list[Item]:
        with self._lock:
            items = list(self._items.values())
        return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)
