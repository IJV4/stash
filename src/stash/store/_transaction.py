import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from stash.store.port import StoreBusyError

_BUSY = "SQLITE_BUSY"
_NESTED = "stash_nested"


def _begin_immediate(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as error:
        if error.sqlite_errorname != _BUSY:
            raise
        raise StoreBusyError(
            "another writer held the stash for longer than the wait; try again"
        ) from error


@contextmanager
def immediate_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    if connection.in_transaction:
        with _savepoint(connection):
            yield
        return
    _begin_immediate(connection)
    try:
        yield
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


@contextmanager
def _savepoint(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute(f"SAVEPOINT {_NESTED}")
    try:
        yield
    except BaseException:
        if connection.in_transaction:
            connection.execute(f"ROLLBACK TO {_NESTED}")
            connection.execute(f"RELEASE {_NESTED}")
        raise
    connection.execute(f"RELEASE {_NESTED}")
