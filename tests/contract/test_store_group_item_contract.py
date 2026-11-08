from dataclasses import replace

import pytest
from builders import LATER, an_item, fetched_item, stored, stored_item, stored_parent
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import Item
from stash.store import (
    ChildHoldsItemsError,
    ParentIsGroupedError,
    Store,
    UnknownItemError,
)


def grouped(read: Item, parent_id: str = "p1") -> Item:
    return replace(read, parent_id=parent_id, updated_at=LATER)


def stored_grouped_parent(store: Store) -> Item:
    stored(store, an_item(id="g1", title="Asia"))
    return stored(store, an_item(id="p1", title="Japan trip", parent_id="g1"))


@on_sqlite
def test_group_item_puts_the_child_under_a_top_level_parent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = stored_item(store)

        # Execute
        store.group_item(grouped(read))

        # Assert
        assert fetched_item(store, "i1") == grouped(read)


@on_sqlite
def test_group_item_of_a_child_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = an_item()

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="i1"):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_of_a_child_deleted_after_it_was_read_does_not_bring_it_back(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = stored_item(store)
        store.delete_item("i1")

        # Execute
        with pytest.raises(UnknownItemError):
            store.group_item(grouped(read))

        # Assert
        assert store.get_item("i1") is None


@on_sqlite
def test_group_item_under_a_parent_that_is_not_stored_raises_unknown_item_error_naming_it(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_under_a_parent_that_is_not_stored_writes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        with pytest.raises(UnknownItemError):
            store.group_item(grouped(read))

        # Assert
        assert store.get_item("i1") == read


@on_sqlite
def test_group_item_under_a_parent_grouped_after_it_was_read_raises_parent_is_grouped_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = stored_item(store)
        stored_grouped_parent(store)

        # Execute / Assert
        with pytest.raises(ParentIsGroupedError, match="p1"):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_under_a_grouped_parent_writes_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        stored_grouped_parent(store)

        # Execute
        with pytest.raises(ParentIsGroupedError):
            store.group_item(grouped(read))

        # Assert
        assert store.get_item("i1") == read


@on_sqlite
def test_group_item_of_a_child_that_gained_a_child_after_it_was_read_raises_child_holds_items(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = stored_item(store)
        stored(store, an_item(id="k1", title="Ramen menu", parent_id="i1"))

        # Execute / Assert
        with pytest.raises(ChildHoldsItemsError, match="i1"):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_of_a_child_that_holds_items_writes_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = stored_item(store)
        stored(store, an_item(id="k1", title="Ramen menu", parent_id="i1"))

        # Execute
        with pytest.raises(ChildHoldsItemsError):
            store.group_item(grouped(read))

        # Assert
        assert store.get_item("i1") == read


@on_sqlite
def test_group_item_under_a_grouped_parent_raises_parent_is_grouped_before_child_holds_items(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        stored_grouped_parent(store)
        stored(store, an_item(id="k1", title="Ramen menu", parent_id="i1"))

        # Execute / Assert
        with pytest.raises(ParentIsGroupedError):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_under_a_missing_parent_raises_unknown_item_error_before_child_holds_items(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        stored(store, an_item(id="k1", title="Ramen menu", parent_id="i1"))

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.group_item(grouped(read))


@on_sqlite
def test_group_item_with_a_child_that_has_no_parent_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(ValueError, match="i1"):
            store.group_item(read)
