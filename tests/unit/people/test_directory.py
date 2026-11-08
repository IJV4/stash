import pytest
from fakes.store_factories import FreshStore
from people_builders import a_directory

from stash.domain import KeyDate, KeyDateKind
from stash.store.port import UnknownPersonError

UNKNOWN_ID = "nobody"


def test_an_added_person_is_found_by_name_with_their_relation_and_aliases() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)

    # Execute
    added = directory.add("Ana", relation="sister", aliases=("Anita",))

    # Assert
    assert store.find_by_name("anita") == added
    assert (added.name, added.relation, added.aliases) == ("Ana", "sister", ("Anita",))


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


def test_a_removed_person_is_no_longer_found() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")

    # Execute
    directory.remove(ana.id)

    # Assert
    assert store.find_by_name("Ana") is None


def test_removing_an_unknown_person_raises_unknown_person() -> None:
    # Execute / Assert
    with pytest.raises(UnknownPersonError):
        a_directory().remove(UNKNOWN_ID)


def test_an_added_key_date_is_kept_for_the_person() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")

    # Execute
    added = directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 14, year=1990, label="Born")

    # Assert
    assert store.key_dates_for(ana.id) == [
        KeyDate(added.id, ana.id, KeyDateKind.BIRTHDAY, "Born", 3, 14, 1990)
    ]


def test_adding_a_key_date_again_with_the_same_kind_and_label_ignoring_case_replaces_it() -> None:
    # Setup
    store = FreshStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.OTHER, 3, 6, label="Graduation")

    # Execute
    corrected = directory.add_key_date(ana.id, KeyDateKind.OTHER, 3, 7, label=" graduation ")

    # Assert
    assert store.key_dates_for(ana.id) == [corrected]


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
