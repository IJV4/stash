import pytest
from builders import an_item, fetched_item, stored
from fakes.racing_item_store import RacingItemStore
from lifecycle_rig import a_lifecycle

from stash.domain import GROUPS_ONE_LEVEL_DEEP, Item
from stash.lifecycle import LifecycleRefused

HOLDS_ITEMS_REFUSAL = f"{GROUPS_ONE_LEVEL_DEEP}: Tokyo ramen already holds items"


def a_store_with_child_and_parent() -> RacingItemStore:
    store = RacingItemStore()
    stored(store, an_item(id="child", title="Tokyo ramen"))
    stored(store, an_item(id="parent", title="Japan trip"))
    return store


def ramen_menu() -> Item:
    return an_item(id="menu", title="Ramen menu", parent_id="child")


def parent_in_a_group() -> Item:
    return an_item(id="parent", title="Japan trip", parent_id="grandparent")


def test_grouping_a_child_that_gained_an_item_meanwhile_is_refused_as_already_holding_items() -> (
    None
):
    # Setup
    store = a_store_with_child_and_parent()
    store.another_writer_saves_before_grouping(ramen_menu())

    # Execute
    with pytest.raises(LifecycleRefused) as raised:
        a_lifecycle(store).group("child", "parent")

    # Assert
    assert str(raised.value) == HOLDS_ITEMS_REFUSAL


def test_a_child_that_gained_an_item_meanwhile_stays_ungrouped() -> None:
    # Setup
    store = a_store_with_child_and_parent()
    store.another_writer_saves_before_grouping(ramen_menu())

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).group("child", "parent")

    # Assert
    assert fetched_item(store, "child").parent_id is None


def test_grouping_under_a_parent_grouped_meanwhile_is_refused_as_one_level_deep() -> None:
    # Setup
    store = a_store_with_child_and_parent()
    stored(store, an_item(id="grandparent", title="Asia"))
    store.another_writer_saves_before_grouping(parent_in_a_group())

    # Execute
    with pytest.raises(LifecycleRefused) as raised:
        a_lifecycle(store).group("child", "parent")

    # Assert
    assert str(raised.value) == GROUPS_ONE_LEVEL_DEEP


def test_a_child_whose_parent_was_grouped_meanwhile_stays_ungrouped() -> None:
    # Setup
    store = a_store_with_child_and_parent()
    stored(store, an_item(id="grandparent", title="Asia"))
    store.another_writer_saves_before_grouping(parent_in_a_group())

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).group("child", "parent")

    # Assert
    assert fetched_item(store, "child").parent_id is None
