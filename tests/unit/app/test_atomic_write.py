import os
from pathlib import Path

from stash.app import write_atomically


def test_a_second_name_for_the_old_file_keeps_the_old_bytes_while_the_path_gets_the_new_ones(
    tmp_path: Path,
) -> None:
    # Setup
    page = tmp_path / "library.html"
    page.write_bytes(b"old")
    old_file = tmp_path / "old.html"
    os.link(page, old_file)

    # Execute
    write_atomically(page, b"new")

    # Assert
    assert (page.read_bytes(), old_file.read_bytes()) == (b"new", b"old")
