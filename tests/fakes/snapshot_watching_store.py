from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date

from fakes.store_factories import FreshStore

from stash.domain import Item, ItemType
from stash.store.port import DEFAULT_PAGE_SIZE

OPENED = "opened"
READ = "read"
RELEASED = "released"


class SnapshotWatchingStore(FreshStore):
    def __init__(
        self, read_failure: Exception | None = None, busy: Exception | None = None
    ) -> None:
        super().__init__()
        self.events: list[str] = []
        self._read_failure = read_failure
        self._busy = busy

    def read_snapshot(self) -> AbstractContextManager[None]:
        return self._snapshot()

    def library(
        self,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        self.events.append(READ)
        if self._read_failure is not None:
            raise self._read_failure
        return super().library(item_type, limit, offset)

    def done_between(self, start: date, end: date) -> list[Item]:
        self.events.append(READ)
        return super().done_between(start, end)

    @contextmanager
    def _snapshot(self) -> Iterator[None]:
        if self._busy is not None:
            raise self._busy
        self.events.append(OPENED)
        try:
            yield
        finally:
            self.events.append(RELEASED)
