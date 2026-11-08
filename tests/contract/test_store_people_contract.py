import pytest
from fakes.store_factories import StoreFactory, on_sqlite
from people_builders import a_person, ids_of_people, stored_person

from stash.store import DuplicateNameError


@on_sqlite
def test_a_saved_person_reads_back_whole(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        person = stored_person(store, aliases=("Anita", "Ani"))

        # Execute
        found = store.get_person("p1")

        # Assert
        assert found == person


@on_sqlite
def test_an_unknown_person_reads_back_as_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.get_person("missing")

        # Assert
        assert found is None


@on_sqlite
def test_saving_a_person_again_under_the_same_id_replaces_them(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        renamed = stored_person(store, name="Ana Rivera-Lopez")

        # Execute
        found = store.get_person("p1")

        # Assert
        assert found == renamed


@on_sqlite
def test_people_are_listed_by_name_ignoring_case_then_id(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="bruno", aliases=())
        stored_person(store, id="p2", name="Alma", aliases=())
        stored_person(store, id="p3", name="Carla", aliases=())

        # Execute
        found = store.list_people()

        # Assert
        assert ids_of_people(found) == ["p2", "p1", "p3"]


@on_sqlite
def test_a_second_person_with_the_same_name_in_another_case_is_refused(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana Rivera", aliases=())

        # Execute / Assert
        with pytest.raises(DuplicateNameError):
            store.save_person(a_person(id="p2", name="ANA RIVERA", aliases=()))


@on_sqlite
def test_a_person_whose_name_is_another_persons_alias_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana Rivera", aliases=("Anita",))

        # Execute / Assert
        with pytest.raises(DuplicateNameError):
            store.save_person(a_person(id="p2", name="anita", aliases=()))


@on_sqlite
def test_a_person_with_an_alias_that_is_another_persons_name_is_refused(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana Rivera", aliases=())

        # Execute / Assert
        with pytest.raises(DuplicateNameError):
            store.save_person(a_person(id="p2", name="Bruno", aliases=("ana rivera",)))


@on_sqlite
def test_a_person_with_an_alias_another_person_already_has_is_refused(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana Rivera", aliases=("Nita",))

        # Execute / Assert
        with pytest.raises(DuplicateNameError):
            store.save_person(a_person(id="p2", name="Bruno", aliases=("NITA",)))


@on_sqlite
def test_a_refused_person_is_not_stored(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana Rivera", aliases=())
        with pytest.raises(DuplicateNameError):
            store.save_person(a_person(id="p2", name="Ana Rivera"))

        # Execute
        found = store.get_person("p2")

        # Assert
        assert found is None


def test_a_duplicate_name_refusal_is_a_value_error() -> None:
    # Assert
    assert issubclass(DuplicateNameError, ValueError)


@on_sqlite
def test_a_person_can_be_found_by_name_ignoring_case(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        person = stored_person(store)

        # Execute
        found = store.find_by_name("ana RIVERA")

        # Assert
        assert found == person


@on_sqlite
def test_a_person_can_be_found_by_alias_ignoring_case(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        person = stored_person(store, aliases=("Anita",))

        # Execute
        found = store.find_by_name("ANITA")

        # Assert
        assert found == person


@on_sqlite
def test_a_name_that_only_partly_matches_finds_nobody(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, name="Ana Rivera", aliases=("Anita",))

        # Execute
        found = store.find_by_name("Ana")

        # Assert
        assert found is None


@on_sqlite
def test_deleting_a_person_removes_them(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.delete_person("p1")

        # Execute
        found = store.get_person("p1")

        # Assert
        assert found is None


@on_sqlite
def test_deleting_an_unknown_person_changes_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        person = stored_person(store)
        store.delete_person("missing")

        # Execute
        found = store.list_people()

        # Assert
        assert found == [person]
