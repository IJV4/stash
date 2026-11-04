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
