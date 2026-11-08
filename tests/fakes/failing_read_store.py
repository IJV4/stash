from fakes.store_factories import FreshStore

from stash.domain import Item, ItemType
from stash.store.port import DEFAULT_PAGE_SIZE


class ReadFailed(Exception):
    pass


class FailingReadStore(FreshStore):
    def get_item(self, item_id: str) -> Item | None:
        raise ReadFailed("database is closed")

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        raise ReadFailed("database is closed")
