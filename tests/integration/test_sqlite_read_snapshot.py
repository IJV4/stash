import sqlite3
from pathlib import Path

import pytest
from fakes.store_factories import opened, two_connections

from stash.store import StoreBusyError

KEY = "library.theme"
BUSY_MESSAGE = "database is locked"
UNRELATED_MESSAGE = "unable to open database file"


class Refused(Exception):
    pass


def a_locked_error(errorname: str | None = None) -> sqlite3.OperationalError:
    if errorname is None:
        return sqlite3.OperationalError(BUSY_MESSAGE)
    error = sqlite3.OperationalError(UNRELATED_MESSAGE)
    error.sqlite_errorname = errorname
    return error


@pytest.mark.integration
def test_a_write_committed_during_the_snapshot_is_not_seen_by_later_reads_inside_it(
    tmp_path: Path,
) -> None:
    # Setup
    with two_connections(tmp_path) as (reader, writer):
        reader.put_setting(KEY, "dark")

        # Execute
        with reader.read_snapshot():
            reader.get_setting(KEY)
            writer.put_setting(KEY, "light")
            seen_inside = reader.get_setting(KEY)

        # Assert
        assert seen_inside == "dark"


@pytest.mark.integration
@pytest.mark.parametrize(
    "error",
    [
        pytest.param(a_locked_error(), id="message-only"),
        pytest.param(a_locked_error("SQLITE_BUSY"), id="busy"),
        pytest.param(a_locked_error("SQLITE_LOCKED"), id="locked"),
    ],
)
def test_a_busy_or_locked_database_inside_the_snapshot_surfaces_as_store_busy(
    tmp_path: Path, error: sqlite3.OperationalError
) -> None:
    # Execute / Assert
    with (
        opened(tmp_path / "stash.db") as reader,
        pytest.raises(StoreBusyError),
        reader.read_snapshot(),
    ):
        raise error


@pytest.mark.integration
def test_a_busy_conversion_keeps_the_sqlite_error_as_its_cause(tmp_path: Path) -> None:
    # Setup
    error = a_locked_error("SQLITE_BUSY")
    with opened(tmp_path / "stash.db") as reader:
        # Execute
        with pytest.raises(StoreBusyError) as refusal, reader.read_snapshot():
            raise error

        # Assert
        assert refusal.value.__cause__ is error


@pytest.mark.integration
def test_any_other_sqlite_error_inside_the_snapshot_propagates_unchanged(tmp_path: Path) -> None:
    # Setup
    error = sqlite3.OperationalError("no such table: nothing")
    with opened(tmp_path / "stash.db") as reader:
        # Execute
        with pytest.raises(sqlite3.OperationalError) as refusal, reader.read_snapshot():
            raise error

        # Assert
        assert refusal.value is error


@pytest.mark.integration
def test_no_transaction_is_left_open_after_an_error_inside_the_snapshot(tmp_path: Path) -> None:
    # Setup
    with two_connections(tmp_path) as (reader, writer):
        reader.put_setting(KEY, "dark")
        with pytest.raises(Refused), reader.read_snapshot():
            reader.get_setting(KEY)
            writer.put_setting(KEY, "light")
            raise Refused

        # Execute
        seen_after = reader.get_setting(KEY)

        # Assert
        assert seen_after == "light"
