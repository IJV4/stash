from pathlib import Path

from cli_rig import CliRig, build_cli_rig


def rig_with_a_kept_book(directory: Path) -> CliRig:
    rig = build_cli_rig(directory)
    book = rig.filed_as("Dune", item_type="book", title="Dune", stage="doing")
    rig.through_lifecycle(lambda lifecycle: lifecycle.complete(book.id, rating=4, keep=True))
    return rig


def test_library_html_writes_the_rendered_library_to_the_path(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "out" / "library.html"

    # Execute
    rig.run("library", "--html", str(page))

    # Assert
    assert "Dune" in page.read_text(encoding="utf-8")


def test_library_html_confirms_the_path_and_exits_0(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "library.html"

    # Execute
    result = rig.run("library", "--html", str(page))

    # Assert
    assert (result.exit_code, result.out) == (0, f"Library written: {page}\n")


def test_library_html_replaces_an_existing_file_whole_and_leaves_no_temporary_file(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "pages" / "library.html"
    page.parent.mkdir()
    page.write_text("stale " * 100_000, encoding="utf-8")

    # Execute
    rig.run("library", "--html", str(page))

    # Assert
    assert ("stale" in page.read_text(encoding="utf-8"), list(page.parent.iterdir())) == (
        False,
        [page],
    )


def test_library_html_refuses_a_path_that_does_not_end_in_html_and_writes_nothing(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "library.txt"

    # Execute
    result = rig.run("library", "--html", str(page))

    # Assert
    assert (result.exit_code, result.out, page.exists()) == (2, "", False)


def test_library_html_names_the_required_extension_when_it_refuses_a_path(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)

    # Execute
    result = rig.run("library", "--html", str(tmp_path / "library.txt"))

    # Assert
    assert "must end in .html" in result.err


def test_library_html_accepts_an_upper_case_extension(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "LIBRARY.HTML"

    # Execute
    result = rig.run("library", "--html", str(page))

    # Assert
    assert (result.exit_code, page.exists()) == (0, True)


def test_library_html_reports_a_path_it_cannot_write_on_standard_error_and_exits_1(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")
    page = blocker / "library.html"

    # Execute
    result = rig.run("library", "--html", str(page))

    # Assert
    assert (result.exit_code, result.out, result.err.startswith(f"cannot write {page}: ")) == (
        1,
        "",
        True,
    )


def test_library_without_html_still_lists_the_kept_items_as_text(tmp_path: Path) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)

    # Execute
    result = rig.run("library")

    # Assert
    assert result.out.endswith("📚 Books: Dune · ⭐4\n")


def test_library_html_leaves_no_temporary_file_when_the_final_replace_fails(
    tmp_path: Path,
) -> None:
    # Setup
    rig = rig_with_a_kept_book(tmp_path)
    page = tmp_path / "pages" / "library.html"
    page.mkdir(parents=True)

    # Execute
    result = rig.run("library", "--html", str(page))

    # Assert
    assert (result.exit_code, list(page.parent.iterdir())) == (1, [page])
