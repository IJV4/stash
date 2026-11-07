import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from stash.store._transaction import immediate_transaction


class Refused(Exception):
    pass


def an_autocommit_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    connection.execute("CREATE TABLE t (n INTEGER)")
    return connection


def counts(connection: sqlite3.Connection) -> int:
    count: int = connection.execute("SELECT count(*) FROM t").fetchone()[0]
    return count


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    with closing(an_autocommit_connection()) as opened:
        yield opened


@pytest.mark.integration
def test_writes_made_inside_the_block_are_committed(connection: sqlite3.Connection) -> None:
    # Execute
    with immediate_transaction(connection):
        connection.execute("INSERT INTO t VALUES (1)")

    # Assert
    assert counts(connection) == 1


@pytest.mark.integration
def test_writes_made_inside_the_block_are_rolled_back_when_it_raises(
    connection: sqlite3.Connection,
) -> None:
    # Execute
    with pytest.raises(Refused), immediate_transaction(connection):
        connection.execute("INSERT INTO t VALUES (1)")
        raise Refused

    # Assert
    assert counts(connection) == 0


@pytest.mark.integration
def test_the_exception_that_aborted_the_block_reaches_the_caller(
    connection: sqlite3.Connection,
) -> None:
    # Execute / Assert
    with pytest.raises(Refused), immediate_transaction(connection):
        raise Refused


@pytest.mark.integration
def test_the_block_is_inside_a_transaction_while_it_runs(connection: sqlite3.Connection) -> None:
    # Execute
    with immediate_transaction(connection):
        inside = connection.in_transaction

    # Assert
    assert inside is True


@pytest.mark.integration
def test_the_block_is_no_longer_in_a_transaction_once_it_ends(
    connection: sqlite3.Connection,
) -> None:
    # Execute
    with immediate_transaction(connection):
        pass

    # Assert
    assert connection.in_transaction is False


@pytest.mark.integration
def test_the_block_takes_the_write_lock_before_its_first_write(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    holder = sqlite3.connect(path, isolation_level=None)
    rival = sqlite3.connect(path, isolation_level=None, timeout=0)

    # Execute / Assert
    with (
        closing(holder),
        closing(rival),
        immediate_transaction(holder),
        pytest.raises(sqlite3.OperationalError, match="locked"),
    ):
        rival.execute("BEGIN IMMEDIATE")


def a_file_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


@pytest.fixture
def plain(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(a_file_connection(tmp_path / "plain.db")) as opened:
        yield opened


@pytest.fixture
def full(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(a_file_connection(tmp_path / "full.db")) as opened:
        opened.execute("CREATE TABLE blobs (data BLOB)")
        opened.execute("INSERT INTO blobs VALUES (zeroblob(10))")
        page_count = opened.execute("PRAGMA page_count").fetchone()[0]
        opened.execute(f"PRAGMA max_page_count={page_count}")
        yield opened


@pytest.fixture
def deferred(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(a_file_connection(tmp_path / "deferred.db")) as opened:
        opened.execute("CREATE TABLE parents (id INTEGER PRIMARY KEY)")
        opened.execute(
            "CREATE TABLE children (parent_id INTEGER REFERENCES parents (id)"
            " DEFERRABLE INITIALLY DEFERRED)"
        )
        yield opened


def fill_the_database(connection: sqlite3.Connection) -> None:
    connection.execute("INSERT INTO blobs VALUES (zeroblob(100000))")


def orphan_a_child(connection: sqlite3.Connection) -> None:
    connection.execute("INSERT INTO children VALUES (1)")


@pytest.mark.integration
def test_an_error_that_makes_sqlite_end_the_transaction_reaches_the_caller_unmasked(
    full: sqlite3.Connection,
) -> None:
    # Execute
    with pytest.raises(sqlite3.OperationalError) as caught, immediate_transaction(full):
        fill_the_database(full)

    # Assert
    assert caught.value.sqlite_errorname == "SQLITE_FULL"


@pytest.mark.integration
def test_an_error_that_makes_sqlite_end_the_transaction_leaves_no_transaction_open(
    full: sqlite3.Connection,
) -> None:
    # Execute
    with pytest.raises(sqlite3.OperationalError), immediate_transaction(full):
        fill_the_database(full)

    # Assert
    assert full.in_transaction is False


@pytest.mark.integration
def test_a_failed_commit_reaches_the_caller_as_the_commit_error(
    deferred: sqlite3.Connection,
) -> None:
    # Execute
    with pytest.raises(sqlite3.IntegrityError) as caught, immediate_transaction(deferred):
        orphan_a_child(deferred)

    # Assert
    assert caught.value.sqlite_errorname == "SQLITE_CONSTRAINT_FOREIGNKEY"


@pytest.mark.integration
def test_a_failed_commit_leaves_no_transaction_open(deferred: sqlite3.Connection) -> None:
    # Execute
    with pytest.raises(sqlite3.IntegrityError), immediate_transaction(deferred):
        orphan_a_child(deferred)

    # Assert
    assert deferred.in_transaction is False


@pytest.mark.integration
def test_a_failed_commit_keeps_the_writes_of_the_block_out_of_the_database(
    deferred: sqlite3.Connection,
) -> None:
    # Setup
    with pytest.raises(sqlite3.IntegrityError), immediate_transaction(deferred):
        orphan_a_child(deferred)

    # Execute
    children = deferred.execute("SELECT count(*) FROM children").fetchone()[0]

    # Assert
    assert children == 0


@pytest.mark.integration
def test_a_commit_with_no_transaction_left_reaches_the_caller_as_the_commit_error(
    plain: sqlite3.Connection,
) -> None:
    # Execute / Assert
    with (
        pytest.raises(sqlite3.OperationalError, match="cannot commit"),
        immediate_transaction(plain),
    ):
        plain.execute("ROLLBACK")
