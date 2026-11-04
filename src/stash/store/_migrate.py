import re
import sqlite3
from collections.abc import Iterator
from importlib.resources import files
from importlib.resources.abc import Traversable

from stash.store._transaction import immediate_transaction

_MIGRATION_NAME = re.compile(r"([0-9]{4})_.*\.sql")


def packaged_migrations() -> Traversable:
    return files("stash.store") / "migrations"


def apply_migrations(connection: sqlite3.Connection, migrations: Traversable) -> None:
    available = _numbered_scripts(migrations)
    current = _schema_version(connection)
    newest = len(available)
    if current > newest:
        raise ValueError(f"database schema version {current} is newer than supported {newest}")
    for version in range(current + 1, newest + 1):
        _apply(connection, version, available[version])


def _numbered_scripts(migrations: Traversable) -> dict[int, str]:
    scripts: dict[int, str] = {}
    for entry in migrations.iterdir():
        matched = _MIGRATION_NAME.fullmatch(entry.name)
        if matched is None:
            continue
        version = int(matched.group(1))
        if version in scripts:
            raise ValueError(f"duplicate migration number {version}")
        scripts[version] = entry.read_text(encoding="utf-8")
    if not scripts:
        raise ValueError("no migrations found")
    if sorted(scripts) != list(range(1, len(scripts) + 1)):
        raise ValueError("migration numbers must be contiguous from 1")
    return scripts


def _schema_version(connection: sqlite3.Connection) -> int:
    version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


def _apply(connection: sqlite3.Connection, version: int, script: str) -> None:
    with immediate_transaction(connection):
        if _schema_version(connection) < version:
            for statement in _statements(script):
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {int(version)}")


def _statements(script: str) -> Iterator[str]:
    *terminated, tail = script.split(";")
    pending = ""
    for fragment in terminated:
        pending += f"{fragment};"
        if sqlite3.complete_statement(pending):
            if pending.strip() != ";":
                yield pending
            pending = ""
    pending += tail
    if pending.strip():
        yield pending
