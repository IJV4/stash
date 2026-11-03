from fakes.memory_store import MemoryStore

from stash.domain import Item


class SaveFailed(Exception):
    pass


class FailingSaveStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_save = False

    def save_item(self, item: Item) -> None:
        if self.fail_next_save:
            self.fail_next_save = False
            raise SaveFailed(item.id)
        super().save_item(item)
