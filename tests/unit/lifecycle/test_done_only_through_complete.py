from collections.abc import Callable
from contextlib import suppress

import pytest
from builders import NON_DONE_STAGES, an_item, an_item_at, fetched_item, stored
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import Lifecycle, LifecycleRefused

OPERATIONS_OTHER_THAN_COMPLETE: dict[str, Callable[[Lifecycle], object]] = {
    "keep": lambda lifecycle: lifecycle.keep("i1", True),
    "unkeep": lambda lifecycle: lifecycle.keep("i1", False),
    "drop": lambda lifecycle: lifecycle.drop("i1", "why"),
    "group": lambda lifecycle: lifecycle.group("i1", "p1"),
    "ungroup": lambda lifecycle: lifecycle.ungroup("i1"),
}


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
@pytest.mark.parametrize(
    "operation", OPERATIONS_OTHER_THAN_COMPLETE.values(), ids=OPERATIONS_OTHER_THAN_COMPLETE.keys()
)
def test_no_operation_other_than_complete_moves_an_item_into_done(
    operation: Callable[[Lifecycle], object], stage: Stage
) -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(stage))
    stored(store, an_item(id="p1", title="Japan trip"))
    lifecycle = a_lifecycle(store)

    # Execute
    with suppress(LifecycleRefused):
        operation(lifecycle)

    # Assert
    assert fetched_item(store, "i1").stage is not Stage.DONE
