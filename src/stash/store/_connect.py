import sqlite3
import time
from datetime import timedelta
from pathlib import Path

_BUSY = "SQLITE_BUSY"
_WAL_SWITCH_DEADLINE_SECONDS = 5.0
_WAL_SWITCH_RETRY_SECONDS = 0.01


def open_connection(path: Path, busy_timeout: timedelta) -> sqlite3.Connection:
    connection = sqlite3.connect(
        str(path),
        timeout=busy_timeout.total_seconds(),
        check_same_thread=False,
        isolation_level=None,
    )
    try:
        _configure(connection)
    except BaseException:
        connection.close()
        raise
    return connection


def _configure(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    _enable_wal(connection)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.create_function("casefold", 1, str.casefold, deterministic=True)


def _enable_wal(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal":
        return
    deadline = time.monotonic() + _WAL_SWITCH_DEADLINE_SECONDS
    while True:
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as error:
            if error.sqlite_errorname != _BUSY or time.monotonic() >= deadline:
                raise
            time.sleep(_WAL_SWITCH_RETRY_SECONDS)
