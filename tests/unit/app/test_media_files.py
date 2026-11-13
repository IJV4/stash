import logging
import os
import stat
from pathlib import Path

from log_records import recording_logs

from stash.app.media_files import DirectoryMediaKeeper

CAPTURE_ID = "c0ffee"
PRIVATE_BYTES = b"SECRET-CONTENT"


def test_a_symlink_or_an_oversized_file_is_not_copied(tmp_path: Path) -> None:
    # Setup
    real = tmp_path / "real.png"
    real.write_bytes(PRIVATE_BYTES)
    link = tmp_path / "link.png"
    link.symlink_to(real)
    big = tmp_path / "big.png"
    big.write_bytes(b"x" * 11)
    keeper = DirectoryMediaKeeper(tmp_path / "media", max_bytes=10)

    # Execute
    with recording_logs("stash.app.media_files") as recorder:
        kept = keeper.keep(CAPTURE_ID, (str(link), str(big)))

    # Assert
    assert kept == (str(link), str(big))
    assert not (tmp_path / "media").exists()
    assert [level for level, _ in recorder.entries()] == [logging.WARNING, logging.WARNING]
    assert all(CAPTURE_ID in text and "SECRET" not in text for _, text in recorder.entries())


def test_an_unknown_extension_is_stored_as_bin(tmp_path: Path) -> None:
    # Setup
    source = tmp_path / "odd.exe"
    source.write_bytes(PRIVATE_BYTES)

    # Execute
    [kept] = DirectoryMediaKeeper(tmp_path / "media").keep(CAPTURE_ID, (str(source),))

    # Assert
    assert kept == str(tmp_path / "media" / f"{CAPTURE_ID}-0.bin")


def test_copies_are_private_to_the_owner(tmp_path: Path) -> None:
    # Setup
    source = tmp_path / "a.ogg"
    source.write_bytes(PRIVATE_BYTES)
    source.chmod(0o644)

    # Execute
    [kept] = DirectoryMediaKeeper(tmp_path / "media").keep(CAPTURE_ID, (str(source),))

    # Assert
    assert stat.S_IMODE(os.stat(kept).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(tmp_path / "media").st_mode) == 0o700


def test_a_directory_is_skipped_as_not_a_regular_file_and_leaks_no_descriptor(
    tmp_path: Path,
) -> None:
    # Setup
    folder = tmp_path / "folder.png"
    folder.mkdir()
    keeper = DirectoryMediaKeeper(tmp_path / "media")
    before = open_descriptors()

    # Execute
    with recording_logs("stash.app.media_files") as recorder:
        kept = keeper.keep(CAPTURE_ID, (str(folder),))

    # Assert
    assert kept == (str(folder),)
    assert "not a regular file" in recorder.entries()[0][1]
    assert open_descriptors() == before


def open_descriptors() -> int:
    return len(os.listdir("/proc/self/fd")) if Path("/proc/self/fd").exists() else 0
