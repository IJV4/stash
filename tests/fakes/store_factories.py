import tempfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest

from stash.domain import RawCapture
from stash.store import Store
from stash.store.sqlite import SqliteStore

StoreFactory = Callable[[], AbstractContextManager[Store]]


IN_MEMORY_DATABASE = Path(":memory:")


class FreshStore(SqliteStore):
    def __init__(self, migrations: Traversable | None = None) -> None:
        super().__init__(IN_MEMORY_DATABASE, migrations)

    def stored_captures(self) -> list[RawCapture]:
        ids = [
            row["id"] for row in self._connection.execute("SELECT id FROM captures ORDER BY rowid")
        ]
        return [capture for capture in map(self.get_capture, ids) if capture is not None]


@contextmanager
def fresh_store() -> Iterator[Store]:
    store = FreshStore()
    try:
        yield store
    finally:
        store.close()


@contextmanager
def opened(path: Path, migrations: Traversable | None = None) -> Iterator[SqliteStore]:
    store = SqliteStore(path, migrations)
    try:
        yield store
    finally:
        store.close()


@contextmanager
def two_connections(directory: Path) -> Iterator[tuple[SqliteStore, SqliteStore]]:
    with opened(directory / "stash.db") as first, opened(directory / "stash.db") as second:
        yield first, second


@contextmanager
def sqlite_store() -> Iterator[Store]:
    with tempfile.TemporaryDirectory() as directory, opened(Path(directory) / "stash.db") as store:
        yield store


on_sqlite = pytest.mark.parametrize("open_store", [sqlite_store], ids=["sqlite"])
