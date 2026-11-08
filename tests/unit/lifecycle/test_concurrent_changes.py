from collections.abc import Callable
from dataclasses import dataclass, replace

import pytest
from builders import (
    PLANNED_FOR,
    a_parent_item,
    an_item,
    an_item_at,
    fetched_item,
    stored,
)
from fakes.busy_store import BusyStore
from fakes.changing_item_store import RETITLED_BY_ANOTHER_WRITER, ChangingItemStore
from fakes.store_factories import FreshStore
from fakes.vanishing_item_store import VanishingItemStore
from lifecycle_rig import a_lifecycle

from stash.domain import Item, Stage
from stash.lifecycle import ItemChanged, Lifecycle, StashBusy, UnknownItem


@dataclass(frozen=True, slots=True)
class Operation:
    item: Item
    run: Callable[[Lifecycle], object]


OPERATIONS = [
    pytest.param(Operation(an_item_at(Stage.DOING), lambda lc: lc.complete("i1")), id="complete"),
    pytest.param(Operation(an_item_at(Stage.DONE), lambda lc: lc.keep("i1", True)), id="keep"),
    pytest.param(Operation(an_item_at(Stage.DONE), lambda lc: lc.reopen("i1")), id="reopen"),
    pytest.param(Operation(an_item_at(Stage.INBOX), lambda lc: lc.drop("i1", None)), id="drop"),
    pytest.param(
        Operation(an_item_at(Stage.PLANNED), lambda lc: lc.didnt_happen("i1", PLANNED_FOR)),
        id="didnt_happen",
    ),
    pytest.param(
        Operation(an_item_at(Stage.INBOX), lambda lc: lc.set_stage("i1", Stage.WANT_TO)),
        id="set_stage",
    ),
    pytest.param(
        Operation(an_item_at(Stage.PLANNED), lambda lc: lc.reschedule("i1", PLANNED_FOR)),
        id="reschedule",
    ),
    pytest.param(Operation(an_item(), lambda lc: lc.group("i1", "p1")), id="group"),
    pytest.param(Operation(an_item(parent_id="p1"), lambda lc: lc.ungroup("i1")), id="ungroup"),
]


def holding(store: FreshStore, operation: Operation) -> None:
    stored(store, a_parent_item())
    stored(store, operation.item)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_an_item_deleted_meanwhile_raises_unknown_item(operation: Operation) -> None:
    # Setup
    store = VanishingItemStore()
    holding(store, operation)
    store.vanish_after_reading_item("i1")

    # Execute
    with pytest.raises(UnknownItem) as raised:
        operation.run(a_lifecycle(store))

    # Assert
    assert raised.value.item_id == "i1"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_an_item_deleted_meanwhile_stays_deleted(operation: Operation) -> None:
    # Setup
    store = VanishingItemStore()
    holding(store, operation)
    store.vanish_after_reading_item("i1")

    # Execute
    with pytest.raises(UnknownItem):
        operation.run(a_lifecycle(store))

    # Assert
    assert store.get_item("i1") is None


@pytest.mark.parametrize("operation", OPERATIONS)
def test_an_item_changed_meanwhile_raises_item_changed_naming_it(operation: Operation) -> None:
    # Setup
    store = ChangingItemStore()
    holding(store, operation)
    store.change_after_reading_item("i1")

    # Execute
    with pytest.raises(ItemChanged) as raised:
        operation.run(a_lifecycle(store))

    # Assert
    assert raised.value.item_id == "i1"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_an_item_changed_meanwhile_keeps_the_other_writers_version(operation: Operation) -> None:
    # Setup
    store = ChangingItemStore()
    holding(store, operation)
    store.change_after_reading_item("i1")

    # Execute
    with pytest.raises(ItemChanged):
        operation.run(a_lifecycle(store))

    # Assert
    assert fetched_item(store, "i1") == replace(operation.item, title=RETITLED_BY_ANOTHER_WRITER)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_a_busy_store_raises_stash_busy(operation: Operation) -> None:
    # Setup
    store = BusyStore()
    holding(store, operation)

    # Execute / Assert
    with pytest.raises(StashBusy):
        operation.run(a_lifecycle(store))
