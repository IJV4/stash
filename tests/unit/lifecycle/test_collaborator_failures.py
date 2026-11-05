from collections.abc import Callable
from datetime import datetime

import pytest
from builders import stored_completion, stored_item
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.lifecycle import Lifecycle

CLOCK_BROKE = "clock broke"
ID_SOURCE_BROKE = "id source broke"

OPERATIONS: dict[str, Callable[[Lifecycle], object]] = {
    "complete": lambda lifecycle: lifecycle.complete("i1"),
    "keep": lambda lifecycle: lifecycle.keep("i1", True),
    "reopen": lambda lifecycle: lifecycle.reopen("i1"),
    "drop": lambda lifecycle: lifecycle.drop("i1", "why"),
    "group": lambda lifecycle: lifecycle.group("i1", "p1"),
    "ungroup": lambda lifecycle: lifecycle.ungroup("i1"),
    "annotate": lambda lifecycle: lifecycle.annotate("o-i1", "notes", ()),
    "rate": lambda lifecycle: lifecycle.rate("o-i1", 3),
}


def a_store_with_a_completed_item_and_a_parent() -> MemoryStore:
    store = MemoryStore()
    stored_completion(store, "i1")
    stored_item(store, id="p1")
    return store


def a_broken_clock() -> datetime:
    raise ValueError(CLOCK_BROKE)


def a_broken_id_source() -> str:
    raise ValueError(ID_SOURCE_BROKE)


@pytest.mark.parametrize("operation", OPERATIONS.values(), ids=OPERATIONS.keys())
def test_a_clock_that_fails_surfaces_its_own_error_not_a_refusal(
    operation: Callable[[Lifecycle], object],
) -> None:
    # Setup
    lifecycle = a_lifecycle(a_store_with_a_completed_item_and_a_parent(), clock=a_broken_clock)

    # Execute
    with pytest.raises(ValueError, match=CLOCK_BROKE):
        operation(lifecycle)


def test_an_id_source_that_fails_surfaces_its_own_error_not_a_refusal() -> None:
    # Setup
    lifecycle = a_lifecycle(a_store_with_a_completed_item_and_a_parent(), new_id=a_broken_id_source)

    # Execute
    with pytest.raises(ValueError, match=ID_SOURCE_BROKE):
        lifecycle.complete("i1")
