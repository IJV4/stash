from datetime import date, timedelta
from pathlib import Path

from backup_builders import a_backups
from fakes.backup_source import FakeBackupSource

from stash.store.backup import BackupName

TODAY = date(2026, 11, 2)
ITEMS = b"three saved items"
FILES_PRESENT_AFTER_TODAYS_BACKUP = 32
NEWEST_KEPT = 30


def test_the_backup_file_is_a_readable_copy_that_holds_the_items(tmp_path: Path) -> None:
    # Setup
    backups = a_backups(FakeBackupSource(ITEMS))

    # Execute
    path = backups.write(tmp_path / "backups", TODAY)

    # Assert
    assert (path.name, path.read_bytes()) == ("stash-20261102.db", ITEMS)


def test_with_32_backups_present_30_remain_and_the_two_oldest_are_gone(tmp_path: Path) -> None:
    # Setup
    days = [TODAY - timedelta(days=back) for back in range(FILES_PRESENT_AFTER_TODAYS_BACKUP)]
    for day in days[1:]:
        (tmp_path / str(BackupName.for_day(day))).write_bytes(b"old")
    (tmp_path / "notes.txt").write_bytes(b"mine")

    # Execute
    a_backups(FakeBackupSource()).write(tmp_path, TODAY)

    # Assert
    remaining = {path.name for path in tmp_path.glob("stash-*.db")}
    assert remaining == {str(BackupName.for_day(day)) for day in days[:NEWEST_KEPT]}
