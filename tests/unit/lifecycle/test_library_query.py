from typing import Any

import pytest

from stash.domain import ItemType
from stash.lifecycle import MAX_LIBRARY_LIMIT, LibraryQuery
from stash.store.port import DEFAULT_PAGE_SIZE

BOOL_LIMIT: Any = True


def test_a_query_by_default_asks_for_every_type_and_one_page() -> None:
    # Execute
    query = LibraryQuery()

    # Assert
    assert (query.item_type, query.limit) == (None, DEFAULT_PAGE_SIZE)


def test_a_query_keeps_the_type_and_limit_it_was_given() -> None:
    # Execute
    query = LibraryQuery(ItemType.BOOK, 7)

    # Assert
    assert (query.item_type, query.limit) == (ItemType.BOOK, 7)


@pytest.mark.parametrize("limit", [1, MAX_LIBRARY_LIMIT])
def test_a_query_accepts_the_smallest_and_largest_limit(limit: int) -> None:
    # Execute
    query = LibraryQuery(limit=limit)

    # Assert
    assert query.limit == limit


@pytest.mark.parametrize("limit", [0, -1, MAX_LIBRARY_LIMIT + 1])
def test_a_query_refuses_a_limit_outside_one_to_fifty(limit: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        LibraryQuery(limit=limit)


def test_a_query_refuses_a_boolean_limit() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        LibraryQuery(limit=BOOL_LIMIT)
