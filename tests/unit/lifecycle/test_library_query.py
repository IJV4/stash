from typing import Any

import pytest

from stash.lifecycle import MAX_LIBRARY_LIMIT, LibraryQuery

BOOL_LIMIT: Any = True


@pytest.mark.parametrize("limit", [0, -1, MAX_LIBRARY_LIMIT + 1])
def test_a_query_refuses_a_limit_outside_one_to_fifty(limit: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        LibraryQuery(limit=limit)


def test_a_query_refuses_a_boolean_limit() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        LibraryQuery(limit=BOOL_LIMIT)
