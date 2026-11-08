from dataclasses import replace

import pytest
from builders import LATER, a_capture, an_item, fetched_item, stored_item, stored_parent
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import ItemType
from stash.store import UnknownCaptureError, UnknownItemError


@on_sqlite
def test_update_item_replaces_the_stored_item_when_it_still_equals_the_one_read(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        store.update_item(read.retyped(ItemType.BOOK, LATER))

        # Assert
        assert store.get_item("i1") == read.retyped(ItemType.BOOK, LATER)


@on_sqlite
def test_update_item_of_an_item_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        read = an_item()

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="i1"):
            store.update_item(read.retyped(ItemType.BOOK, LATER))


@on_sqlite
def test_update_item_of_an_item_deleted_after_it_was_read_does_not_bring_it_back(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        store.delete_item("i1")

        # Execute
        with pytest.raises(UnknownItemError):
            store.update_item(read.retyped(ItemType.BOOK, LATER))

        # Assert
        assert store.get_item("i1") is None


@on_sqlite
def test_update_item_under_a_parent_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.update_item(replace(read, parent_id="p1"))


@on_sqlite
def test_update_item_under_a_parent_that_is_not_stored_writes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        with pytest.raises(UnknownItemError):
            store.update_item(replace(read, parent_id="p1"))

        # Assert
        assert store.get_item("i1") == read


@on_sqlite
def test_update_item_under_a_stored_parent_groups_it(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        read = an_item()
        store.save_item(read)

        # Execute
        store.update_item(replace(read, parent_id="p1"))

        # Assert
        assert fetched_item(store, "i1").parent_id == "p1"


@on_sqlite
def test_update_item_moved_to_an_unknown_capture_raises_unknown_capture_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(UnknownCaptureError, match="c9"):
            store.update_item(replace(read, capture_id="c9"))


@on_sqlite
def test_update_item_moved_to_an_unknown_capture_writes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        with pytest.raises(UnknownCaptureError):
            store.update_item(replace(read, capture_id="c9"))

        # Assert
        assert store.get_item("i1") == read
