import pytest
from fakes.store_factories import FreshStore
from people_builders import a_directory

from stash.domain import KeyDateKind
from stash.store.port import UnknownPersonError

UNKNOWN_ID = "nobody"


def test_renaming_a_person_replaces_the_name_they_answer_to() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")

    # Execute
    renamed = directory.rename(ana.id, "Annabel")

    # Assert
    assert (renamed.name, store.find_by_name("Ana")) == ("Annabel", None)


def test_renaming_an_unknown_person_raises_unknown_person() -> None:
    # Execute / Assert
    with pytest.raises(UnknownPersonError):
        a_directory().rename(UNKNOWN_ID, "Ana")


def test_an_added_alias_makes_the_person_answer_to_it_beside_their_other_names() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana", aliases=("Anita",))

    # Execute
    with_alias = directory.add_alias(ana.id, "Nana")

    # Assert
    assert store.find_by_name("nana") == with_alias


def test_adding_an_alias_to_an_unknown_person_raises_unknown_person() -> None:
    # Execute / Assert
    with pytest.raises(UnknownPersonError):
        a_directory().add_alias(UNKNOWN_ID, "Nana")


def test_adding_a_key_date_with_another_label_keeps_both() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.OTHER, 3, 6, label="Graduation")

    # Execute
    directory.add_key_date(ana.id, KeyDateKind.OTHER, 3, 7, label="Wedding")

    # Assert
    assert len(store.key_dates_for(ana.id)) == 2


def test_adding_a_key_date_of_another_kind_with_the_same_label_keeps_both() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6)

    # Execute
    directory.add_key_date(ana.id, KeyDateKind.ANNIVERSARY, 3, 7)

    # Assert
    assert len(store.key_dates_for(ana.id)) == 2
