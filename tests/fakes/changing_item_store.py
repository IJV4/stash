from dataclasses import replace

from fakes.memory_store import MemoryStore

from stash.domain import Item

RETITLED_BY_ANOTHER_WRITER = "Retitled by another writer"


class ChangingItemStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self._changing_items: set[str] = set()

    def change_after_reading_item(self, item_id: str) -> None:
        self._changing_items.add(item_id)

    def get_item(self, item_id: str) -> Item | None:
        item = super().get_item(item_id)
        if item is not None and item_id in self._changing_items:
            self._changing_items.discard(item_id)
            self.save_item(replace(item, title=RETITLED_BY_ANOTHER_WRITER))
        return item
