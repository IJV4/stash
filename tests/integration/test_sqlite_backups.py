import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from backup_builders import a_backups
from builders import a_capture, an_item
from fakes.store_factories import opened

from stash.store import BackupError

TODAY = date(2026, 11, 2)


@pytest.mark.integration
def test_a_backup_of_the_sqlite_store_opens_as_a_database_holding_the_saved_item(
    tmp_path: Path,
) -> None:
    # Setup
    capture = a_capture()
    item = an_item(id=capture.id, capture_id=capture.id)
    with opened(tmp_path / "stash.db") as store:
        store.add_capture(capture)
        store.save_item(item)

        # Execute
        path = a_backups(store).write(tmp_path / "backups", TODAY)

    # Assert
    with closing(sqlite3.connect(path)) as copy:
        titles = copy.execute("SELECT title FROM items").fetchall()
    assert titles == [(item.title,)]


@pytest.mark.integration
def test_a_backup_of_the_sqlite_store_reopens_as_a_store_with_the_item(tmp_path: Path) -> None:
    # Setup
    capture = a_capture()
    item = an_item(id=capture.id, capture_id=capture.id)
    with opened(tmp_path / "stash.db") as store:
        store.add_capture(capture)
        store.save_item(item)
        path = a_backups(store).write(tmp_path / "backups", TODAY)

    # Execute
    with opened(path) as restored:
        found = restored.get_item(item.id)

    # Assert
    assert found == item


@pytest.mark.integration
def test_a_sqlite_failure_while_backing_up_is_translated_to_backup_error(tmp_path: Path) -> None:
    # Setup
    unwritable_target = tmp_path / "a-directory"
    unwritable_target.mkdir()

    # Execute / Assert
    with opened(tmp_path / "stash.db") as store, pytest.raises(BackupError):
        store.backup_to(unwritable_target)


@pytest.mark.integration
def test_a_backup_into_a_missing_directory_raises_backup_error_and_leaves_nothing(
    tmp_path: Path,
) -> None:
    # Setup
    target = tmp_path / "missing" / "backup.db"

    # Execute / Assert
    with opened(tmp_path / "stash.db") as store, pytest.raises(BackupError):
        store.backup_to(target)
    assert not target.parent.exists()


@pytest.mark.integration
def test_a_failed_backup_leaves_an_existing_target_untouched(tmp_path: Path) -> None:
    # Setup
    target = tmp_path / "backup.db"
    with closing(sqlite3.connect(target)) as previous:
        previous.execute("CREATE TABLE marker (id INTEGER)")
    before = target.read_bytes()

    # Execute
    with (
        opened(tmp_path / "stash.db") as store,
        patch("shutil.copyfile", side_effect=OSError("x")),
        pytest.raises(BackupError),
    ):
        store.backup_to(target)

    # Assert
    assert (target.read_bytes(), sorted(p.name for p in tmp_path.iterdir())) == (
        before,
        ["backup.db", "stash.db"],
    )
