from people_builders import a_directory

NOBODY_YET: tuple[str, ...] = ()


def test_names_and_aliases_resolve_to_their_person_ignoring_case() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana", aliases=("Anita",))
    bea = directory.add("Bea")

    # Execute
    resolution = directory.resolve(["ANITA", "bea"])

    # Assert
    assert resolution.linked == (ana, bea)


def test_a_name_with_surrounding_whitespace_resolves_to_its_person() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana")

    # Execute
    resolution = directory.resolve(["  Ana\n"])

    # Assert
    assert resolution.linked == (ana,)


def test_a_person_named_twice_under_different_names_is_linked_once() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana", aliases=("Anita",))

    # Execute
    resolution = directory.resolve(["Ana", "ana", "Anita"])

    # Assert
    assert resolution.linked == (ana,)


def test_a_name_nobody_answers_to_is_unknown_and_never_matched_fuzzily() -> None:
    # Setup
    directory = a_directory()
    directory.add("Ana")

    # Execute
    resolution = directory.resolve(["Anna"])

    # Assert
    assert (resolution.linked, resolution.unknown) == (NOBODY_YET, ("Anna",))


def test_unknown_names_are_stripped_deduplicated_ignoring_case_and_kept_in_first_seen_order() -> (
    None
):
    # Setup
    directory = a_directory()

    # Execute
    resolution = directory.resolve([" Cleo", "Bea ", "cleo", "Bea"])

    # Assert
    assert resolution.unknown == ("Cleo", "Bea")


def test_blank_names_are_neither_linked_nor_unknown() -> None:
    # Setup
    directory = a_directory()
    directory.add("Ana")

    # Execute
    resolution = directory.resolve(["", "   "])

    # Assert
    assert (resolution.linked, resolution.unknown) == (NOBODY_YET, NOBODY_YET)
