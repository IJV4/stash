from fakes.store_factories import FreshStore

from stash.domain import Item
from stash.store.port import DEFAULT_PAGE_SIZE


class SearchFailed(Exception):
    pass


class FailingSearchStore(FreshStore):
    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        raise SearchFailed("database is closed")
