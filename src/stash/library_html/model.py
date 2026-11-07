from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from stash.domain import Item, ItemType, Outcome, Stage, require_aware

SECTION_LIMIT = 200
EARLIEST_DAY = date(1970, 1, 1)


class LibrarySource(Protocol):
    def library(
        self, item_type: ItemType | None = None, limit: int = 20, offset: int = 0
    ) -> list[Item]: ...

    def done_between(self, start: date, end: date) -> list[Item]: ...

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Item]: ...

    def outcomes_for(self, item_id: str) -> list[Outcome]: ...


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    item: Item
    outcomes: list[Outcome]
    media_notes: str | None = None

    @property
    def latest_outcome(self) -> Outcome | None:
        if not self.outcomes:
            return None
        return max(self.outcomes, key=lambda outcome: (outcome.completed_on, outcome.recorded_at))


@dataclass(frozen=True, slots=True)
class LibrarySnapshot:
    generated_at: datetime
    kept: Mapping[ItemType, list[LibraryEntry]]
    done_by_year: Mapping[int, list[LibraryEntry]]
    want_to: Mapping[ItemType, list[Item]]
    dropped: list[Item]


def _all_pages(fetch: Callable[[int, int], list[Item]], page_size: int) -> list[Item]:
    items: list[Item] = []
    while page := fetch(page_size, len(items)):
        items.extend(page)
    return items


def _by_type(items: list[Item]) -> dict[ItemType, list[Item]]:
    grouped: dict[ItemType, list[Item]] = defaultdict(list)
    for item in items:
        grouped[item.item_type].append(item)
    return dict(grouped)


def _entry(store: LibrarySource, item: Item) -> LibraryEntry:
    return LibraryEntry(item, store.outcomes_for(item.id))


def _done_by_year(store: LibrarySource, today: date) -> dict[int, list[LibraryEntry]]:
    by_year: dict[int, list[LibraryEntry]] = defaultdict(list)
    for item in store.done_between(EARLIEST_DAY, today):
        if item.stage is Stage.DROPPED:
            continue
        entry = _entry(store, item)
        if entry.latest_outcome is not None:
            by_year[entry.latest_outcome.completed_on.year].append(entry)
    return dict(by_year)


def _stage_items(store: LibrarySource, stage: Stage, page_size: int) -> list[Item]:
    return _all_pages(
        lambda limit, offset: store.list_items(stage=stage, limit=limit, offset=offset),
        page_size,
    )


def build_snapshot(
    store: LibrarySource, now: datetime, page_size: int = SECTION_LIMIT
) -> LibrarySnapshot:
    require_aware("now", now)
    kept = _all_pages(lambda limit, offset: store.library(limit=limit, offset=offset), page_size)
    return LibrarySnapshot(
        generated_at=now,
        kept={
            item_type: [_entry(store, item) for item in items]
            for item_type, items in _by_type(kept).items()
        },
        done_by_year=_done_by_year(store, now.date()),
        want_to=_by_type(_stage_items(store, Stage.WANT_TO, page_size)),
        dropped=_stage_items(store, Stage.DROPPED, page_size),
    )
