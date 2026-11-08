from dataclasses import replace

import pytest
from builders import LATER, a_capture, an_item, fetched_item, stored_item, stored_parent
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import ItemType
from stash.store import StaleItemError, UnknownCaptureError, UnknownItemError


@on_sqlite
def test_update_item_replaces_the_stored_item_when_it_still_equals_the_one_read(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)

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
            store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)


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
            store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)

        # Assert
        assert store.get_item("i1") is None


@on_sqlite
def test_update_item_of_an_item_changed_after_it_was_read_raises_stale_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        store.save_item(read.retyped(ItemType.MEDIA, LATER))

        # Execute / Assert
        with pytest.raises(StaleItemError, match="i1"):
            store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)


@on_sqlite
def test_update_item_of_an_item_changed_in_the_same_clock_tick_raises_stale_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        store.save_item(replace(read, title="Retitled by another writer"))

        # Execute / Assert
        with pytest.raises(StaleItemError, match="i1"):
            store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)


@on_sqlite
def test_update_item_of_a_changed_item_keeps_the_other_writers_version(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)
        other = replace(read, title="Retitled by another writer")
        store.save_item(other)

        # Execute
        with pytest.raises(StaleItemError):
            store.update_item(read.retyped(ItemType.BOOK, LATER), replacing=read)

        # Assert
        assert store.get_item("i1") == other


@on_sqlite
def test_update_item_with_a_replaced_item_of_another_id_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(ValueError, match="i2"):
            store.update_item(read, replacing=replace(read, id="i2"))


@on_sqlite
def test_update_item_under_a_parent_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.update_item(replace(read, parent_id="p1"), replacing=read)


@on_sqlite
def test_update_item_under_a_parent_that_is_not_stored_writes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        with pytest.raises(UnknownItemError):
            store.update_item(replace(read, parent_id="p1"), replacing=read)

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
        store.update_item(replace(read, parent_id="p1"), replacing=read)

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
            store.update_item(replace(read, capture_id="c9"), replacing=read)


@on_sqlite
def test_update_item_moved_to_an_unknown_capture_writes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        read = stored_item(store)

        # Execute
        with pytest.raises(UnknownCaptureError):
            store.update_item(replace(read, capture_id="c9"), replacing=read)

        # Assert
        assert store.get_item("i1") == read
