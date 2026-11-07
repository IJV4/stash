from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from builders import LOS_ANGELES, a_capture, an_item, an_outcome
from fakes.memory_store import MemoryStore

from stash.domain import (
    DROP_REASON_LIMIT,
    MAX_TAKEAWAYS,
    OUTCOME_NOTES_LIMIT,
    TAKEAWAY_LIMIT,
    Item,
    ItemType,
    Outcome,
    Stage,
)
from stash.domain.item import TITLE_LIMIT
from stash.library_html import LibraryEntry, LibrarySnapshot, build_snapshot, render_library
from stash.library_html.model import SECTION_LIMIT

LOCAL_NOW = datetime(2026, 11, 7, 9, 30, tzinfo=LOS_ANGELES)
LONG_NOTE_LENGTH = 4096


def rendered(store: MemoryStore, now: datetime = LOCAL_NOW, page_size: int = SECTION_LIMIT) -> str:
    return render_library(build_snapshot(store, now, page_size))


def appearing_order(page: str, needles: list[str]) -> list[str]:
    return sorted(needles, key=page.index)


class _Markup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.attributes: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        self.attributes.update(name for name, _ in attrs)
        self.hrefs.extend(value for name, value in attrs if name == "href" and value is not None)


def parsed_markup(page: str) -> _Markup:
    markup = _Markup()
    markup.feed(page)
    return markup


def store_of_kept_items(count: int) -> MemoryStore:
    store = MemoryStore()
    store.add_capture(a_capture())
    for number in range(count):
        item_id = f"i{number}"
        store.save_item(an_item(id=item_id, title=f"Item {number}", stage=Stage.DONE, kept=True))
        store.add_outcome(an_outcome(id=f"o{number}", item_id=item_id))
    return store


def a_section_of(count: int, field: str) -> LibrarySnapshot:
    entries = [LibraryEntry(an_item(kept=True), [])] * count
    items = [an_item(stage=Stage.WANT_TO)] * count
    sections: dict[str, Any] = {
        "kept": {ItemType.RECIPE: entries},
        "done_by_year": {2026: entries},
        "want_to": {ItemType.RECIPE: items},
        "dropped": items,
    }
    return a_snapshot(**{field: sections[field]})


def a_maximal_library(entries_per_section: int) -> LibrarySnapshot:
    outcome = an_outcome(
        notes="n" * OUTCOME_NOTES_LIMIT, takeaways=("t" * TAKEAWAY_LIMIT,) * MAX_TAKEAWAYS
    )
    item = an_item(kept=True, title="x" * TITLE_LIMIT, note="m" * LONG_NOTE_LENGTH)
    entries = [LibraryEntry(item, [outcome])] * entries_per_section
    unfinished = [an_item(title=item.title, note=item.note)] * entries_per_section
    dropped = [an_item(stage=Stage.DROPPED, title=item.title, drop_reason="d" * DROP_REASON_LIMIT)]
    return a_snapshot(
        kept={ItemType.RECIPE: entries},
        done_by_year={2026: entries},
        want_to={ItemType.RECIPE: unfinished},
        dropped=dropped * entries_per_section,
    )


def a_snapshot(**overrides: Any) -> LibrarySnapshot:
    fields: dict[str, Any] = {
        "generated_at": LOCAL_NOW,
        "kept": {},
        "done_by_year": {},
        "want_to": {},
        "dropped": [],
    }
    return LibrarySnapshot(**{**fields, **overrides})


def a_kept_snapshot(item: Item, outcomes: list[Outcome] | None = None) -> LibrarySnapshot:
    return a_snapshot(kept={item.item_type: [LibraryEntry(item, outcomes or [])]})


def with_unchecked_source_url(item: Item, url: str) -> Item:
    object.__setattr__(item, "source_url", url)
    return item
