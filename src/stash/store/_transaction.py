import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from stash.store.port import StoreBusyError

_BUSY = "SQLITE_BUSY"


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
    _begin_immediate(connection)
    try:
        yield
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
