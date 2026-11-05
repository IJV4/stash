from dataclasses import dataclass

from stash.domain import ItemType
from stash.store.port import DEFAULT_PAGE_SIZE

MAX_LIBRARY_LIMIT = 50
MIN_LIBRARY_LIMIT = 1


@dataclass(frozen=True, slots=True)
class LibraryQuery:
    item_type: ItemType | None = None
    limit: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not MIN_LIBRARY_LIMIT <= self.limit <= MAX_LIBRARY_LIMIT:
            raise ValueError(f"limit must be between {MIN_LIBRARY_LIMIT} and {MAX_LIBRARY_LIMIT}")


DEFAULT_LIBRARY_QUERY = LibraryQuery()
