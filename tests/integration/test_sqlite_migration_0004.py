import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from builders import a_capture, an_item
from fakes.store_factories import opened
from migration_sets import (
    INIT_SCRIPT,
    LIFECYCLE_SCRIPT,
    STEPS_SCRIPT,
    packaged_scripts,
    write_migrations,
)

STEPS_SCHEMA_VERSION = 3
PEOPLE_SCHEMA_VERSION = 4
PEOPLE_TABLES = ("people", "key_dates", "item_people")


def steps_database(tmp_path: Path) -> Path:
    path = tmp_path / "stash.db"
    steps = write_migrations(
        tmp_path / "steps", packaged_scripts(INIT_SCRIPT, LIFECYCLE_SCRIPT, STEPS_SCRIPT)
    )
    with opened(path, steps) as store:
        store.add_capture(a_capture())
        store.save_item(an_item())
    assert schema_version(path) == STEPS_SCHEMA_VERSION
    return path


def schema_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


@pytest.mark.integration
def test_a_steps_database_migrates_to_the_people_schema_version(tmp_path: Path) -> None:
    # Setup
    path = steps_database(tmp_path)

    # Execute
    with opened(path):
        pass

    # Assert
    assert schema_version(path) == PEOPLE_SCHEMA_VERSION


@pytest.mark.integration
def test_a_steps_database_keeps_its_item_after_migrating(tmp_path: Path) -> None:
    # Setup
    path = steps_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = store.get_item("i1")

    # Assert
    assert found == an_item()


@pytest.mark.integration
def test_a_steps_database_gains_the_empty_people_tables(tmp_path: Path) -> None:
    # Setup
    path = steps_database(tmp_path)

    # Execute
    with opened(path), closing(sqlite3.connect(path)) as raw:
        counts = [
            raw.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in PEOPLE_TABLES
        ]

    # Assert
    assert counts == [0, 0, 0]
