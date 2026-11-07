import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from builders import LATER, fetched_item, stored_item
from fakes.store_factories import opened

from stash.domain import ItemType

EQUIVALENT_TO_BASE_AT_PLUS_TWO = "2026-11-02T14:00:00+02:00"


def rewrite_updated_at(path: Path, text: str) -> None:
    with closing(sqlite3.connect(path, isolation_level=None)) as side:
        side.execute("UPDATE items SET updated_at = ? WHERE id = 'i1'", (text,))


@pytest.mark.integration
def test_an_item_stored_with_an_equivalent_but_differently_written_instant_is_not_stale(
    tmp_path: Path,
) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as store:
        stored_item(store)
        rewrite_updated_at(path, EQUIVALENT_TO_BASE_AT_PLUS_TWO)
        read = fetched_item(store, "i1")

        # Execute
        store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)

        # Assert
        assert store.get_item("i1") == read.retyped(ItemType.BOOK, LATER)
