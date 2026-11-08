from collections.abc import Sequence

from fakes.store_factories import FreshStore

from stash.domain import Item, Outcome, Step
from stash.store import StoreBusyError


class BusyStore(FreshStore):
    def update_item(self, item: Item, *, replacing: Item) -> None:
        raise StoreBusyError

    def record_completion(self, item: Item, outcome: Outcome, *, replacing: Item) -> None:
        raise StoreBusyError

    def group_item(self, child: Item, *, replacing: Item) -> None:
        raise StoreBusyError

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        raise StoreBusyError
