import pytest
from builders import an_item, minutes_after, stored_item, titles
from fakes.store_factories import StoreFactory, on_sqlite
from people_builders import a_key_date, ids_of_people, stored_person

from stash.domain import ItemType
from stash.store import UnknownItemError, UnknownPersonError


@on_sqlite
def test_a_linked_person_is_listed_for_the_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")
        stored_person(store, id="p1", name="Ana", aliases=())
        store.link("i1", "p1")

        # Execute
        found = store.people_for("i1")

        # Assert
        assert ids_of_people(found) == ["p1"]


@on_sqlite
def test_an_item_with_no_links_has_no_people(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")

        # Execute
        found = store.people_for("i1")

        # Assert
        assert found == []


@on_sqlite
def test_an_items_people_are_listed_by_name(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")
        stored_person(store, id="p1", name="Bruno", aliases=())
        stored_person(store, id="p2", name="Alma", aliases=())
        store.link("i1", "p1")
        store.link("i1", "p2")

        # Execute
        found = store.people_for("i1")

        # Assert
        assert ids_of_people(found) == ["p2", "p1"]


@on_sqlite
def test_linking_twice_leaves_one_link(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")
        stored_person(store, id="p1", name="Ana", aliases=())
        store.link("i1", "p1")
        store.link("i1", "p1")

        # Execute
        found = store.people_for("i1")

        # Assert
        assert ids_of_people(found) == ["p1"]


@on_sqlite
def test_an_unlinked_person_is_no_longer_listed_for_the_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")
        stored_person(store, id="p1", name="Ana", aliases=())
        store.link("i1", "p1")
        store.unlink("i1", "p1")

        # Execute
        found = store.people_for("i1")

        # Assert
        assert found == []


@on_sqlite
def test_unlinking_a_person_who_was_never_linked_changes_nothing(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")
        stored_person(store, id="p1", name="Ana", aliases=())
        store.unlink("i1", "p1")

        # Execute
        found = store.get_person("p1")

        # Assert
        assert found is not None


@on_sqlite
def test_linking_an_unknown_item_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())

        # Execute / Assert
        with pytest.raises(UnknownItemError):
            store.link("missing", "p1")


@on_sqlite
def test_linking_an_unknown_person_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1")

        # Execute / Assert
        with pytest.raises(UnknownPersonError):
            store.link("i1", "missing")


@on_sqlite
def test_a_persons_items_are_listed_newest_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())
        stored_item(store, id="i1", title="Old", created_at=minutes_after(1))
        store.save_item(an_item(id="i2", title="New", created_at=minutes_after(2)))
        store.link("i1", "p1")
        store.link("i2", "p1")

        # Execute
        found = store.items_for("p1")

        # Assert
        assert titles(found) == ["New", "Old"]


@on_sqlite
def test_a_persons_items_can_be_limited_to_one_type(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())
        stored_item(store, id="i1", title="Mug", item_type=ItemType.GIFT)
        store.save_item(an_item(id="i2", title="Cafe", item_type=ItemType.PLACE))
        store.link("i1", "p1")
        store.link("i2", "p1")

        # Execute
        found = store.items_for("p1", ItemType.GIFT)

        # Assert
        assert titles(found) == ["Mug"]


@on_sqlite
def test_a_persons_items_leave_out_other_peoples_items(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())
        stored_person(store, id="p2", name="Bruno", aliases=())
        stored_item(store, id="i1", title="Mug")
        store.link("i1", "p2")

        # Execute
        found = store.items_for("p1")

        # Assert
        assert found == []


@on_sqlite
def test_deleting_a_person_keeps_their_items(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1")
        item = stored_item(store, id="i1", people=("Ana Rivera",))
        store.link("i1", "p1")
        store.delete_person("p1")

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found == item


@on_sqlite
def test_deleting_a_person_unlinks_their_items(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1")
        stored_item(store, id="i1")
        store.link("i1", "p1")
        store.delete_person("p1")
        stored_person(store, id="p1")

        # Execute
        found = store.items_for("p1")

        # Assert
        assert found == []


@on_sqlite
def test_deleting_an_item_removes_its_links(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1")
        stored_item(store, id="i1")
        store.link("i1", "p1")
        store.delete_item_if_untouched("i1")
        store.save_item(an_item(id="i1"))

        # Execute
        found = store.people_for("i1")

        # Assert
        assert found == []


@on_sqlite
def test_deleting_an_item_keeps_the_person_and_their_key_dates(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1")
        store.save_key_date(a_key_date())
        stored_item(store, id="i1")
        store.link("i1", "p1")
        store.delete_item_if_untouched("i1")

        # Execute
        found = store.key_dates_for("p1")

        # Assert
        assert found == [a_key_date()]


@on_sqlite
def test_items_naming_people_leave_out_items_that_name_nobody(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1", title="Mug", people=("Ana",))
        stored_item(store, id="i2", title="Cafe", people=())

        # Execute
        found = store.items_naming_people()

        # Assert
        assert titles(found) == ["Mug"]


@on_sqlite
def test_items_naming_people_are_listed_newest_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="i1", title="Old", people=("Ana",), created_at=minutes_after(1))
        stored_item(store, id="i2", title="New", people=("Ana",), created_at=minutes_after(2))

        # Execute
        found = store.items_naming_people()

        # Assert
        assert titles(found) == ["New", "Old"]
