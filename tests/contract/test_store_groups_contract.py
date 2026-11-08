from dataclasses import replace

import pytest
from builders import (
    a_capture,
    a_parent_item,
    an_item,
    an_item_at,
    minutes_after,
    stored,
    stored_item,
    stored_parent,
    titles,
)
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import Stage
from stash.store import UnknownItemError


@on_sqlite
def test_a_kept_item_grouped_under_a_parent_round_trips_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        item = replace(an_item(), kept=True, parent_id="p1")
        store.save_item(item)

        # Execute
        found = store.get_item(item.id)

        # Assert
        assert found == item


@on_sqlite
def test_a_dropped_item_keeps_its_drop_reason_through_a_round_trip(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored(store, an_item_at(Stage.DROPPED, drop_reason="too expensive"))

        # Execute
        found = store.get_item(item.id)

        # Assert
        assert found == item


@on_sqlite
def test_saving_an_item_under_a_parent_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.save_item(an_item(parent_id="p1"))


@on_sqlite
def test_saving_an_item_under_a_parent_that_is_not_stored_stores_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute
        with pytest.raises(UnknownItemError):
            store.save_item(an_item(parent_id="p1"))

        # Assert
        assert store.get_item("i1") is None


@on_sqlite
def test_saving_a_stored_item_again_updates_its_lifecycle_fields(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        store.save_item(an_item_at(Stage.DONE))
        regrouped = replace(an_item_at(Stage.DONE), kept=True, parent_id="p1")
        store.save_item(regrouped)

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found == regrouped


@on_sqlite
def test_saving_a_stored_item_again_updates_its_drop_reason(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored(store, an_item_at(Stage.DROPPED, drop_reason="too expensive"))
        store.save_item(an_item_at(Stage.DROPPED, drop_reason="no longer wanted"))

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found == an_item_at(Stage.DROPPED, drop_reason="no longer wanted")


@on_sqlite
def test_deleting_a_parent_leaves_its_children_stored_without_a_parent(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        child = an_item(parent_id="p1", kept=True, tags=("food",), updated_at=minutes_after(7))
        store.save_item(child)
        store.delete_item("p1")

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found == replace(child, parent_id=None)


@on_sqlite
def test_deleting_a_parent_leaves_its_other_groups_alone(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        store.save_item(an_item(id="q1", title="Other trip"))
        other_child = an_item(id="i2", parent_id="q1")
        store.save_item(other_child)
        store.delete_item("p1")

        # Execute
        found = store.get_item("i2")

        # Assert
        assert found == other_child


@on_sqlite
def test_deleting_a_child_leaves_its_parent_stored(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        store.save_item(an_item(parent_id="p1"))
        store.delete_item("i1")

        # Execute
        found = store.get_item("p1")

        # Assert
        assert found == a_parent_item()


@on_sqlite
def test_children_of_lists_the_items_grouped_under_a_parent_oldest_created_first(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        for minute, name in [(2, "second"), (1, "first"), (3, "third")]:
            stored_item(
                store, id=name, title=name, parent_id="p1", created_at=minutes_after(minute)
            )

        # Execute
        listed = store.children_of("p1")

        # Assert
        assert titles(listed) == ["first", "second", "third"]


@on_sqlite
def test_children_of_lists_the_lower_id_first_when_created_together(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        for name in ["b", "a"]:
            stored_item(store, id=name, title=name, parent_id="p1")

        # Execute
        listed = store.children_of("p1")

        # Assert
        assert titles(listed) == ["a", "b"]


@on_sqlite
def test_children_of_leaves_out_the_children_of_other_parents(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        store.save_item(an_item(id="q1", title="Other trip"))
        store.save_item(an_item(id="mine", title="mine", parent_id="p1"))
        store.save_item(an_item(id="theirs", title="theirs", parent_id="q1"))

        # Execute
        listed = store.children_of("p1")

        # Assert
        assert titles(listed) == ["mine"]


@on_sqlite
def test_children_of_a_childless_parent_is_empty(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)

        # Execute
        listed = store.children_of("p1")

        # Assert
        assert listed == []


@on_sqlite
def test_children_of_an_unknown_id_is_empty(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        listed = store.children_of("missing")

        # Assert
        assert listed == []
