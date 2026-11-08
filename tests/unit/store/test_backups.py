import logging
import os
from datetime import date, timedelta
from pathlib import Path

import pytest
from backup_builders import BACKED_UP_AT, a_backups
from fakes.backup_source import FakeBackupSource
from fakes.store_factories import FreshStore
from log_records import recording_logs

from stash.store import BACKUP_LAST_SUCCESS_KEY, BackupError, StoreBusyError
from stash.store.backup import BackupName

TODAY = date(2026, 11, 2)
SOURCE_BYTES = b"the items"
TODAY_EPOCH = 1_793_000_000
LOOK_ALIKES = [
    "notes.txt",
    "stash.db",
    "stash-2026.db",
    "stash-20200101.db.bak",
    "stash-20200101.db\n",
    "old-stash-20200101.db",
    "stash-20201340.db",
]


def backup_names(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


def seed(directory: Path, days_back: range) -> None:
    for back in days_back:
        (directory / str(BackupName.for_day(TODAY - timedelta(days=back)))).write_bytes(b"old")


def test_writing_a_backup_returns_the_path_named_after_today(tmp_path: Path) -> None:
    # Execute
    path = a_backups(FakeBackupSource()).write(tmp_path, TODAY)

    # Assert
    assert path == tmp_path / "stash-20261102.db"


def test_the_backup_file_holds_what_the_source_wrote(tmp_path: Path) -> None:
    # Execute
    path = a_backups(FakeBackupSource(SOURCE_BYTES)).write(tmp_path, TODAY)

    # Assert
    assert path.read_bytes() == SOURCE_BYTES


def test_the_directory_is_created_when_it_does_not_exist(tmp_path: Path) -> None:
    # Setup
    directory = tmp_path / "nas" / "stash-backups"

    # Execute
    a_backups(FakeBackupSource()).write(directory, TODAY)

    # Assert
    assert backup_names(directory) == ["stash-20261102.db"]


def test_the_source_is_copied_into_a_temporary_file_in_the_same_directory(tmp_path: Path) -> None:
    # Setup
    source = FakeBackupSource()

    # Execute
    a_backups(source).write(tmp_path, TODAY)

    # Assert
    [target] = source.targets
    assert (target.parent, BackupName.parse(target.name)) == (tmp_path, None)


def test_no_temporary_file_is_left_behind_after_a_backup(tmp_path: Path) -> None:
    # Execute
    a_backups(FakeBackupSource()).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == ["stash-20261102.db"]


def test_running_twice_on_one_day_replaces_that_days_file(tmp_path: Path) -> None:
    # Setup
    a_backups(FakeBackupSource(b"first")).write(tmp_path, TODAY)

    # Execute
    path = a_backups(FakeBackupSource(b"second")).write(tmp_path, TODAY)

    # Assert
    assert (path.read_bytes(), backup_names(tmp_path)) == (b"second", ["stash-20261102.db"])


def test_a_failed_copy_raises_a_backup_error_naming_the_directory_and_the_cause(
    tmp_path: Path,
) -> None:
    # Setup
    source = FakeBackupSource()
    source.fail_with = OSError("disk full")

    # Execute / Assert
    with pytest.raises(BackupError, match=f"cannot write to {tmp_path}: disk full"):
        a_backups(source).write(tmp_path, TODAY)


def test_a_failed_copy_chains_the_original_error(tmp_path: Path) -> None:
    # Setup
    cause = OSError("disk full")
    source = FakeBackupSource()
    source.fail_with = cause

    # Execute
    with pytest.raises(BackupError) as failure:
        a_backups(source).write(tmp_path, TODAY)

    # Assert
    assert failure.value.__cause__ is cause


def test_a_target_that_is_a_file_raises_a_backup_error_naming_it(tmp_path: Path) -> None:
    # Setup
    target = tmp_path / "file"
    target.write_text("not a directory")

    # Execute / Assert
    with pytest.raises(BackupError, match=f"cannot write to {target}"):
        a_backups(FakeBackupSource()).write(target, TODAY)


def test_a_target_below_a_file_raises_a_backup_error_naming_it(tmp_path: Path) -> None:
    # Setup
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    target = blocker / "nas"

    # Execute / Assert
    with pytest.raises(BackupError, match=f"cannot write to {target}"):
        a_backups(FakeBackupSource()).write(target, TODAY)


def test_a_backup_name_taken_by_a_directory_raises_a_backup_error(tmp_path: Path) -> None:
    # Setup
    (tmp_path / "stash-20261102.db").mkdir()

    # Execute / Assert
    with pytest.raises(BackupError, match=f"cannot write to {tmp_path}"):
        a_backups(FakeBackupSource()).write(tmp_path, TODAY)


def test_a_failed_copy_leaves_no_temporary_file(tmp_path: Path) -> None:
    # Setup
    source = FakeBackupSource()
    source.fail_with = OSError("disk full")

    # Execute
    with pytest.raises(BackupError, match="disk full"):
        a_backups(source).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == []


def test_a_failed_copy_keeps_the_previous_backup_of_the_day_intact(tmp_path: Path) -> None:
    # Setup
    a_backups(FakeBackupSource(b"good")).write(tmp_path, TODAY)
    failing = FakeBackupSource()
    failing.fail_with = OSError("disk full")

    # Execute
    with pytest.raises(BackupError, match="disk full"):
        a_backups(failing).write(tmp_path, TODAY)

    # Assert
    assert (tmp_path / "stash-20261102.db").read_bytes() == b"good"


def test_a_failed_copy_does_not_prune_older_backups(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 4))
    failing = FakeBackupSource()
    failing.fail_with = OSError("disk full")

    # Execute
    with pytest.raises(BackupError, match="disk full"):
        a_backups(failing, keep=2).write(tmp_path, TODAY)

    # Assert
    assert len(backup_names(tmp_path)) == 3


def test_a_failed_copy_that_is_not_an_exception_subclass_still_removes_the_temporary_file(
    tmp_path: Path,
) -> None:
    # Setup
    source = FakeBackupSource()
    source.fail_with = KeyboardInterrupt()

    # Execute
    with pytest.raises(KeyboardInterrupt):
        a_backups(source).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == []


def test_only_the_newest_backups_are_kept(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 5))

    # Execute
    a_backups(FakeBackupSource(), keep=3).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == [
        "stash-20261031.db",
        "stash-20261101.db",
        "stash-20261102.db",
    ]


def test_thirty_backups_are_kept_unless_told_otherwise(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 41))

    # Execute
    a_backups(FakeBackupSource()).write(tmp_path, TODAY)

    # Assert
    assert len(backup_names(tmp_path)) == 30


def test_the_newest_by_name_is_kept_whatever_the_modification_times_say(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 3))
    oldest = tmp_path / "stash-20261031.db"
    os.utime(oldest, (TODAY_EPOCH, TODAY_EPOCH))

    # Execute
    a_backups(FakeBackupSource(), keep=2).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == ["stash-20261101.db", "stash-20261102.db"]


def test_keeping_one_backup_leaves_only_todays(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 3))

    # Execute
    a_backups(FakeBackupSource(), keep=1).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == ["stash-20261102.db"]


@pytest.mark.parametrize("filename", LOOK_ALIKES)
def test_a_file_that_only_looks_like_a_backup_is_never_removed(
    tmp_path: Path, filename: str
) -> None:
    # Setup
    (tmp_path / filename).write_bytes(b"not mine")
    seed(tmp_path, range(1, 4))

    # Execute
    a_backups(FakeBackupSource(), keep=1).write(tmp_path, TODAY)

    # Assert
    assert (tmp_path / filename).read_bytes() == b"not mine"


def test_a_directory_named_like_a_backup_is_never_removed(tmp_path: Path) -> None:
    # Setup
    (tmp_path / "stash-20200101.db").mkdir()

    # Execute
    a_backups(FakeBackupSource(), keep=1).write(tmp_path, TODAY)

    # Assert
    assert (tmp_path / "stash-20200101.db").is_dir()


@pytest.mark.parametrize("keep", [0, -1])
def test_keeping_fewer_than_one_backup_is_rejected(keep: int) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="keep"):
        a_backups(FakeBackupSource(), keep=keep)


def refuse_to_remove(path: Path) -> None:
    raise PermissionError(f"read-only share: {path}")


def test_a_failure_while_pruning_does_not_fail_the_write(tmp_path: Path) -> None:
    # Setup
    seed(tmp_path, range(1, 4))
    backups = a_backups(FakeBackupSource(SOURCE_BYTES), keep=2, remove=refuse_to_remove)

    # Execute
    path = backups.write(tmp_path, TODAY)

    # Assert
    assert path.read_bytes() == SOURCE_BYTES


def test_a_failure_while_pruning_is_logged_as_a_warning_naming_only_the_error_type(
    tmp_path: Path,
) -> None:
    # Setup
    seed(tmp_path, range(1, 4))
    backups = a_backups(FakeBackupSource(), keep=2, remove=refuse_to_remove)

    # Execute
    with recording_logs("stash.store.backup") as logs:
        backups.write(tmp_path, TODAY)

    # Assert
    assert logs.entries() == [(logging.WARNING, "could not prune old backups: PermissionError")]


def test_a_backup_error_from_the_source_propagates_and_leaves_no_temporary_file(
    tmp_path: Path,
) -> None:
    # Setup
    source = FakeBackupSource()
    source.fail_with = BackupError("database is locked")

    # Execute
    with pytest.raises(BackupError, match="database is locked"):
        a_backups(source).write(tmp_path, TODAY)

    # Assert
    assert backup_names(tmp_path) == []


def test_a_successful_backup_records_when_it_happened(tmp_path: Path) -> None:
    # Setup
    settings = FreshStore()

    # Execute
    a_backups(FakeBackupSource(), settings).write(tmp_path, TODAY)

    # Assert
    assert settings.get_setting(BACKUP_LAST_SUCCESS_KEY) == BACKED_UP_AT.isoformat()


def test_a_failed_copy_records_no_success(tmp_path: Path) -> None:
    # Setup
    settings = FreshStore()
    source = FakeBackupSource()
    source.fail_with = OSError("disk full")

    # Execute
    with pytest.raises(BackupError):
        a_backups(source, settings).write(tmp_path, TODAY)

    # Assert
    assert settings.get_setting(BACKUP_LAST_SUCCESS_KEY) is None


class LockedSettings:
    def put_setting(self, key: str, value: str) -> None:
        raise StoreBusyError


def test_a_backup_whose_success_cannot_be_recorded_is_still_written_and_returned(
    tmp_path: Path,
) -> None:
    # Execute
    path = a_backups(FakeBackupSource(SOURCE_BYTES), LockedSettings()).write(tmp_path, TODAY)

    # Assert
    assert path.read_bytes() == SOURCE_BYTES


def test_a_failure_recording_the_success_is_logged_as_a_warning_naming_only_the_error_type(
    tmp_path: Path,
) -> None:
    # Execute
    with recording_logs("stash.store.backup") as logs:
        a_backups(FakeBackupSource(), LockedSettings()).write(tmp_path, TODAY)

    # Assert
    assert logs.entries() == [(logging.WARNING, "could not record the backup time: StoreBusyError")]
