import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from stash.store.port import StoreBusyError

_BUSY = "SQLITE_BUSY"
_BUSY_OR_LOCKED = frozenset({_BUSY, "SQLITE_LOCKED"})
_LOCKED_MESSAGE = "database is locked"


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


def _is_busy_or_locked(error: sqlite3.OperationalError) -> bool:
    name = getattr(error, "sqlite_errorname", None)
    return name in _BUSY_OR_LOCKED or _LOCKED_MESSAGE in str(error)


@contextmanager
def read_snapshot(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute("BEGIN")
    try:
        yield
    except sqlite3.OperationalError as error:
        if not _is_busy_or_locked(error):
            raise
        raise StoreBusyError("the stash was busy while reading; try again") from error
    finally:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
