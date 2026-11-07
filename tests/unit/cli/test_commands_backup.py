import io
from datetime import date
from pathlib import Path

import pytest
from backup_builders import a_backups
from fakes.backup_source import FakeBackupSource

from stash.cli.commands import backup
from stash.cli.failure import CommandFailed

TODAY = date(2026, 11, 2)


def test_backup_writes_todays_file_into_the_directory_and_prints_its_path(
    tmp_path: Path,
) -> None:
    # Setup
    out = io.StringIO()

    # Execute
    exit_code = backup(a_backups(FakeBackupSource(b"items")), TODAY, tmp_path / "nas", out)

    # Assert
    written = tmp_path / "nas" / "stash-20261102.db"
    assert (exit_code, out.getvalue(), written.read_bytes()) == (
        0,
        f"Backup written: {written}\n",
        b"items",
    )


def unwritable_target(tmp_path: Path) -> Path:
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    return blocker / "nas"


def test_backup_into_a_directory_that_cannot_be_written_fails_with_exit_code_1(
    tmp_path: Path,
) -> None:
    # Execute
    with pytest.raises(CommandFailed) as failure:
        backup(a_backups(FakeBackupSource()), TODAY, unwritable_target(tmp_path), io.StringIO())

    # Assert
    assert failure.value.exit_code == 1


def test_backup_into_a_directory_that_cannot_be_written_names_the_directory(
    tmp_path: Path,
) -> None:
    # Setup
    target = unwritable_target(tmp_path)

    # Execute
    with pytest.raises(CommandFailed) as failure:
        backup(a_backups(FakeBackupSource()), TODAY, target, io.StringIO())

    # Assert
    assert str(failure.value).startswith(f"cannot write a backup to {target}: ")
