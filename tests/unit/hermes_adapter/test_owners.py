from stash.hermes_adapter.owners import Owners


def test_parsing_nothing_gives_no_owners() -> None:
    # Setup
    raw = None

    # Execute
    owners = Owners.parse(raw)

    # Assert
    assert owners == Owners(())


def test_parsing_an_empty_string_gives_no_owners() -> None:
    # Setup
    raw = ""

    # Execute
    owners = Owners.parse(raw)

    # Assert
    assert owners == Owners(())


def test_parsing_only_blank_entries_gives_no_owners() -> None:
    # Setup
    raw = " , ,  ,"

    # Execute
    owners = Owners.parse(raw)

    # Assert
    assert owners == Owners(())


def test_parsing_trims_the_spaces_around_each_user_id() -> None:
    # Setup
    raw = "  12 ,  34 "

    # Execute
    owners = Owners.parse(raw)

    # Assert
    assert owners == Owners(("12", "34"))


def test_parsing_collapses_duplicate_user_ids() -> None:
    # Setup
    raw = "12,12, 12"

    # Execute
    owners = Owners.parse(raw)

    # Assert
    assert owners == Owners(("12",))


def test_an_owner_user_id_is_admitted() -> None:
    # Setup
    owners = Owners.parse("12,34")

    # Execute
    admitted = owners.admits_user("34")

    # Assert
    assert admitted is True


def test_a_user_id_that_is_not_an_owner_is_not_admitted() -> None:
    # Setup
    owners = Owners.parse("12,34")

    # Execute
    admitted = owners.admits_user("56")

    # Assert
    assert admitted is False


def test_an_empty_owner_set_admits_nobody() -> None:
    # Setup
    owners = Owners.parse(None)

    # Execute
    admitted = owners.admits_user("12")

    # Assert
    assert admitted is False


def test_an_empty_owner_set_is_reported_as_admitting_nobody() -> None:
    # Setup
    owners = Owners.parse(" , ")

    # Execute
    nobody = owners.admits_nobody()

    # Assert
    assert nobody is True


def test_an_owner_set_with_one_owner_does_not_admit_nobody() -> None:
    # Setup
    owners = Owners.parse("12")

    # Execute
    nobody = owners.admits_nobody()

    # Assert
    assert nobody is False


def test_the_first_id_is_the_first_one_listed_not_the_smallest() -> None:
    # Setup
    owners = Owners.parse("77, 12, 34")

    # Execute
    first = owners.first_id()

    # Assert
    assert first == "77"


def test_an_empty_owner_set_has_no_first_id() -> None:
    # Setup
    owners = Owners.parse(None)

    # Execute
    first = owners.first_id()

    # Assert
    assert first is None
