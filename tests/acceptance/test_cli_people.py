from pathlib import Path

from cli_rig import CliRig, build_cli_rig

from stash.domain import KeyDateKind
from stash.people import PeopleDirectory

ANA_LINE = "Ana (wife) — birthday Sat Mar 6"
CY_LINE = "Cy (friend) — anniversary Fri Nov 20"


def know_the_family(directory: PeopleDirectory) -> None:
    ana = directory.add("Ana", "wife")
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6)
    cy = directory.add("Cy", "friend")
    directory.add_key_date(cy.id, KeyDateKind.ANNIVERSARY, 11, 20)
    directory.add("Bo")


def rig_that_knows_the_family(directory: Path) -> CliRig:
    rig = build_cli_rig(directory)
    rig.through_people(know_the_family)
    return rig


def test_people_lists_each_person_with_the_next_key_date_soonest_first(tmp_path: Path) -> None:
    # Setup
    rig = rig_that_knows_the_family(tmp_path)

    # Execute
    result = rig.run("people")

    # Assert
    assert (result.exit_code, result.lines()) == (0, [CY_LINE, ANA_LINE, "Bo"])


def test_people_with_nobody_saved_prints_no_people_yet(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    result = rig.run("people")

    # Assert
    assert (result.exit_code, result.out) == (0, "No people yet.\n")


def test_people_upcoming_lists_only_those_whose_next_key_date_is_within_the_days(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_that_knows_the_family(tmp_path)

    # Execute
    result = rig.run("people", "--upcoming", "18")

    # Assert
    assert (result.exit_code, result.lines()) == (0, [CY_LINE])


def test_people_upcoming_with_nothing_in_the_window_says_so(tmp_path: Path) -> None:
    # Setup
    rig = rig_that_knows_the_family(tmp_path)

    # Execute
    result = rig.run("people", "--upcoming", "17")

    # Assert
    assert (result.exit_code, result.out) == (0, "No key dates coming up.\n")


def test_a_linked_persons_details_never_appear_in_stash_list_or_stash_library(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    book = rig.filed_as("Dune", item_type="book", title="Dune", stage="doing")
    rig.through_lifecycle(lambda lifecycle: lifecycle.complete(book.id, rating=4, keep=True))
    rig.through_people(
        lambda directory: directory.link(
            book.id, directory.add("Marguerite", "spouse", ["Daisy"]).id
        )
    )

    # Execute
    shown = rig.run("list").out + rig.run("library").out

    # Assert
    assert (
        "Dune" in shown,
        [text for text in ("Marguerite", "spouse", "Daisy") if text in shown],
    ) == (
        True,
        [],
    )
