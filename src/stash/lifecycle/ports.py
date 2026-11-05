from typing import Protocol

from stash.domain import Item, ItemType, Outcome
from stash.store.port import DEFAULT_PAGE_SIZE


class LifecycleStore(Protocol):
    def get_item(self, item_id: str) -> Item | None: ...

    def save_item(self, item: Item) -> None: ...

    def record_completion(self, item: Item, outcome: Outcome) -> None: ...

    def save_outcome(self, outcome: Outcome) -> None: ...

    def outcomes_for(self, item_id: str) -> list[Outcome]: ...

    def get_outcome(self, outcome_id: str) -> Outcome | None: ...

    def children_of(self, parent_id: str) -> list[Item]: ...

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]: ...
