from collections.abc import Callable

import pytest
from builders import LATER, an_item, store_holding, stored
from fakes.memory_store import MemoryStore
from fakes.vanishing_item_store import VanishingItemStore
from lifecycle_rig import a_lifecycle

from stash.domain import GROUPS_ONE_LEVEL_DEEP, Item
from stash.lifecycle import LifecycleRefused, UnknownItem

PARENT_HAS_A_PARENT = "parent-has-a-parent"
CHILD_HOLDS_ITEMS = "child-holds-items"
BOTH = "both"


def child_item() -> Item:
    return an_item(id="child", title="Tokyo ramen")


def parent_item() -> Item:
    return an_item(id="parent", title="Japan trip")


def grandparent_item() -> Item:
    return an_item(id="grandparent", title="Asia")


def parent_in_a_group() -> Item:
    return an_item(id="parent", title="Japan trip", parent_id="grandparent")


def grandchild_item() -> Item:
    return an_item(id="grandchild", title="Ramen menu", parent_id="child")


REFUSED_ROWS: dict[str, tuple[Callable[[], MemoryStore], str, str]] = {
    "item-is-its-own-parent": (
        lambda: store_holding(child_item()),
        "child",
        "child",
    ),
    "item-is-its-own-parent-and-holds-items": (
        lambda: store_holding(child_item(), grandchild_item()),
        "child",
        "child",
    ),
    PARENT_HAS_A_PARENT: (
        lambda: store_holding(child_item(), grandparent_item(), parent_in_a_group()),
        "child",
        "parent",
    ),
    CHILD_HOLDS_ITEMS: (
        lambda: store_holding(child_item(), grandchild_item(), parent_item()),
        "child",
        "parent",
    ),
    BOTH: (
        lambda: store_holding(
            child_item(), grandchild_item(), grandparent_item(), parent_in_a_group()
        ),
        "child",
        "parent",
    ),
}
ONE_LEVEL_ROWS = [PARENT_HAS_A_PARENT, CHILD_HOLDS_ITEMS, BOTH]


@pytest.mark.parametrize("row", REFUSED_ROWS)
def test_grouping_is_refused_when_the_domain_or_the_one_level_rule_forbids_it(row: str) -> None:
    # Setup
    build, child_id, parent_id = REFUSED_ROWS[row]
    lifecycle = a_lifecycle(build())

    # Execute
    with pytest.raises(LifecycleRefused):
        lifecycle.group(child_id, parent_id)


@pytest.mark.parametrize("row", REFUSED_ROWS)
def test_a_refused_grouping_changes_nothing_in_the_store(row: str) -> None:
    # Setup
    build, child_id, parent_id = REFUSED_ROWS[row]
    store = build()
    before = store.list_items()

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).group(child_id, parent_id)

    # Assert
    assert store.list_items() == before


@pytest.mark.parametrize("row", ONE_LEVEL_ROWS)
def test_grouping_into_or_out_of_a_group_says_groups_are_one_level_deep(row: str) -> None:
    # Setup
    build, child_id, parent_id = REFUSED_ROWS[row]
    lifecycle = a_lifecycle(build())

    # Execute
    with pytest.raises(LifecycleRefused, match=GROUPS_ONE_LEVEL_DEEP):
        lifecycle.group(child_id, parent_id)


def test_grouping_an_item_under_itself_says_it_cannot_be_its_own_parent() -> None:
    # Setup
    lifecycle = a_lifecycle(store_holding(child_item()))

    # Execute
    with pytest.raises(LifecycleRefused, match="cannot be its own parent"):
        lifecycle.group("child", "child")


def test_grouping_an_item_that_holds_items_names_the_item_in_the_refusal() -> None:
    # Setup
    lifecycle = a_lifecycle(store_holding(child_item(), grandchild_item(), parent_item()))

    # Execute
    with pytest.raises(LifecycleRefused, match="Tokyo ramen already holds items"):
        lifecycle.group("child", "parent")


def test_grouping_an_item_under_another_sets_its_parent_and_stores_it() -> None:
    # Setup
    store = store_holding(child_item(), parent_item())

    # Execute
    grouped = a_lifecycle(store, clock=lambda: LATER).group("child", "parent")

    # Assert
    assert (grouped.parent_id, grouped.updated_at, store.get_item("child")) == (
        "parent",
        LATER,
        grouped,
    )


def test_grouping_an_unknown_child_raises_unknown_item_naming_the_child() -> None:
    # Setup
    lifecycle = a_lifecycle(store_holding(parent_item()))

    # Execute
    with pytest.raises(UnknownItem) as raised:
        lifecycle.group("no-child", "parent")

    # Assert
    assert raised.value.item_id == "no-child"


def test_grouping_under_an_unknown_parent_raises_unknown_item_naming_the_parent() -> None:
    # Setup
    lifecycle = a_lifecycle(store_holding(child_item()))

    # Execute
    with pytest.raises(UnknownItem) as raised:
        lifecycle.group("child", "no-parent")

    # Assert
    assert raised.value.item_id == "no-parent"


def test_grouping_under_a_parent_deleted_between_reading_and_writing_raises_unknown_item() -> None:
    # Setup
    store = VanishingItemStore()
    stored(store, child_item())
    stored(store, parent_item())
    store.vanish_after_reading_item("parent")

    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(store).group("child", "parent")

    # Assert
    assert raised.value.item_id == "parent"


def test_ungrouping_an_item_clears_its_parent_and_stores_it() -> None:
    # Setup
    store = store_holding(parent_item(), an_item(id="child", parent_id="parent"))

    # Execute
    ungrouped = a_lifecycle(store, clock=lambda: LATER).ungroup("child")

    # Assert
    assert (ungrouped.parent_id, ungrouped.updated_at, store.get_item("child")) == (
        None,
        LATER,
        ungrouped,
    )


def test_ungrouping_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(MemoryStore()).ungroup("nope")

    # Assert
    assert raised.value.item_id == "nope"
