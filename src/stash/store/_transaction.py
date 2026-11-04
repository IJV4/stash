import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def immediate_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise
