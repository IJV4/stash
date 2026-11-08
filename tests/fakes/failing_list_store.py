from fakes.store_factories import FreshStore

from stash.domain import Item, ItemType, Stage
from stash.store.port import DEFAULT_PAGE_SIZE


class ListFailed(Exception):
    pass


class FailingListStore(FreshStore):
    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        raise ListFailed("database is closed")
