import tempfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from importlib.resources.abc import Traversable
from pathlib import Path

import pytest
from fakes.memory_store import MemoryStore

from stash.store import Store
from stash.store.sqlite import SqliteStore

StoreFactory = Callable[[], AbstractContextManager[Store]]


@contextmanager
def memory_store() -> Iterator[Store]:
    yield MemoryStore()


@contextmanager
def opened(path: Path, migrations: Traversable | None = None) -> Iterator[SqliteStore]:
    store = SqliteStore(path, migrations)
    try:
        yield store
    finally:
        store.close()


@contextmanager
def sqlite_store() -> Iterator[Store]:
    with tempfile.TemporaryDirectory() as directory, opened(Path(directory) / "stash.db") as store:
        yield store


all_stores = pytest.mark.parametrize(
    "open_store", [memory_store, sqlite_store], ids=["memory", "sqlite"]
)
