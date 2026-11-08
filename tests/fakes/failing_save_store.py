from fakes.store_factories import FreshStore

from stash.domain import Item


class SaveFailed(Exception):
    pass


class FailingSaveStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_save = False

    def save_item(self, item: Item) -> None:
        self._fail_if_asked(item)
        super().save_item(item)

    def update_item(self, item: Item) -> None:
        self._fail_if_asked(item)
        super().update_item(item)

    def _fail_if_asked(self, item: Item) -> None:
        if self.fail_next_save:
            self.fail_next_save = False
            raise SaveFailed(item.id)
