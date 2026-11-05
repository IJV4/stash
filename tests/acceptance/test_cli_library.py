from pathlib import Path

from cli_rig import build_cli_rig


def test_the_library_lists_a_kept_book_with_its_id_and_rating_after_it_was_finished_and_kept(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    book = rig.filed_as("Dune", item_type="book", title="Dune", stage="doing")
    rig.through_lifecycle(lambda lifecycle: lifecycle.complete(book.id, rating=4, keep=True))

    # Execute
    result = rig.run("library", "--type", "book")

    # Assert
    assert (result.exit_code, result.out) == (0, f"{book.id}  📚 Books: Dune · ⭐4\n")


def test_the_library_with_nothing_kept_prints_no_items_and_exits_0(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.filed_as("Dune", item_type="book", title="Dune", stage="doing")

    # Execute
    result = rig.run("library")

    # Assert
    assert (result.exit_code, result.out) == (0, "No items.\n")


def test_show_prints_the_item_its_outcome_and_the_children_of_its_group(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    trip = rig.filed_as("Japan trip", message_id="m1", item_type="plan", title="Japan trip")
    ramen = rig.filed_as("Tokyo ramen", message_id="m2", item_type="place", title="Tokyo ramen")
    rig.through_lifecycle(lambda lifecycle: lifecycle.group(ramen.id, trip.id))
    rig.through_lifecycle(
        lambda lifecycle: lifecycle.complete(
            trip.id,
            rating=5,
            notes="Cherry blossoms",
            takeaways=("Book early", "Carry cash"),
            keep=True,
        )
    )

    # Execute
    result = rig.run("show", trip.id)

    # Assert
    assert (result.exit_code, result.lines()) == (
        0,
        [
            "Plans · Japan trip · Done · 📚 in library",
            "city: Tokyo",
            "Done 2026-11-02 · ⭐5",
            "  Cherry blossoms",
            "  • Book early",
            "  • Carry cash",
            "In this group:",
            "  Places · Tokyo ramen · Want to",
        ],
    )


def test_show_of_an_unknown_id_prints_no_item_on_standard_error_and_exits_1(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    result = rig.run("show", "nope")

    # Assert
    assert (result.exit_code, result.out, result.err) == (1, "", "no item 'nope'\n")
