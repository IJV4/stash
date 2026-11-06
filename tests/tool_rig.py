import json
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from builders import BASE, stored_completion, stored_item
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import Item, ItemType, Outcome, Stage
from stash.hermes_adapter.lifecycle_tools import LifecycleTools

Snapshot = tuple[tuple[Item, tuple[Outcome, ...]], ...]
EVERYTHING = 1000
WANT_TO_ITEM = "w1"
DONE_ITEM = "d1"
DONE_ITEM_OUTCOME = "o-d1"
PARENT_ITEM = "p1"


def answer_of(raw: str) -> dict[str, Any]:
    answer: dict[str, Any] = json.loads(raw)
    return answer


def calling(tools: Mapping[str, Any], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return answer_of(tools[name].handler(arguments))


def store_snapshot(store: MemoryStore) -> Snapshot:
    return tuple(
        (item, tuple(store.outcomes_for(item.id))) for item in store.list_items(limit=EVERYTHING)
    )


def a_tool_store() -> MemoryStore:
    store = MemoryStore()
    stored_item(store, id=WANT_TO_ITEM, title="Dune", item_type=ItemType.BOOK, stage=Stage.WANT_TO)
    stored_completion(store, DONE_ITEM)
    stored_item(store, id=PARENT_ITEM, title="Japan trip")
    return store


def lifecycle_tools_over(
    store: MemoryStore, clock: Callable[[], datetime] = lambda: BASE
) -> LifecycleTools:
    return LifecycleTools(a_lifecycle(store, clock=clock))
