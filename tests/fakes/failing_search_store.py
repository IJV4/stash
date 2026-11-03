from fakes.memory_store import MemoryStore

from stash.domain import Item
from stash.store.port import DEFAULT_PAGE_SIZE


class SearchFailed(Exception):
    pass


class FailingSearchStore(MemoryStore):
    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        raise SearchFailed("database is closed")
