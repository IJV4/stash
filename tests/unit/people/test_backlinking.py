from builders import stored_item
from fakes.faulty_store import FaultyStore, StoreFault
from fakes.store_factories import FreshStore
from log_records import recording_logs
from people_builders import a_directory, ids_of_people

from stash.store import Store


def linked_item_ids(store: Store, person_id: str) -> list[str]:
    return [item.id for item in store.items_for(person_id)]


def test_adding_a_person_does_not_link_items_naming_someone_with_a_similar_name() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="i1", people=("Anabel",))
    directory = a_directory(store)

    # Execute
    ana = directory.add("Ana")

    # Assert
    assert linked_item_ids(store, ana.id) == []


def test_renaming_a_person_links_the_items_naming_their_new_name() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    stored_item(store, id="i1", people=("Annabel",))

    # Execute
    directory.rename(ana.id, "Annabel")

    # Assert
    assert linked_item_ids(store, ana.id) == ["i1"]


def test_adding_an_alias_links_the_items_naming_that_alias() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    stored_item(store, id="i1", people=("Nana",))

    # Execute
    directory.add_alias(ana.id, "Nana")

    # Assert
    assert linked_item_ids(store, ana.id) == ["i1"]


def test_adding_an_alias_leaves_an_already_linked_item_linked_once() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="i1", people=("Ana",))
    directory = a_directory(store)
    ana = directory.add("Ana")

    # Execute
    directory.add_alias(ana.id, "Nana")

    # Assert
    assert ids_of_people(store.people_for("i1")) == [ana.id]


def test_a_failure_while_linking_existing_items_is_logged_and_the_person_is_still_added() -> None:
    # Setup
    store = FaultyStore(fail_on={"link": StoreFault("link")})
    stored_item(store, id="i1", people=("Ana",))
    directory = a_directory(store)

    # Execute
    with recording_logs("stash.people") as recorder:
        ana = directory.add("Ana")

    # Assert
    assert (store.get_person(ana.id), len(recorder.entries())) == (ana, 1)


def test_adding_a_person_links_the_items_already_naming_them_ignoring_case_and_spacing() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="i1", people=(" ana ",))
    directory = a_directory(store)

    # Execute
    ana = directory.add("Ana")

    # Assert
    assert [item.id for item in store.items_for(ana.id)] == ["i1"]
