from fakes.memory_store import MemoryStore

from stash.domain import Item, Outcome
from stash.store import StoreBusyError


class BusyStore(MemoryStore):
    def update_item(self, item: Item, *, replacing: Item) -> None:
        raise StoreBusyError

    def record_completion(self, item: Item, outcome: Outcome, *, replacing: Item) -> None:
        raise StoreBusyError

    def group_item(self, child: Item, *, replacing: Item) -> None:
        raise StoreBusyError
