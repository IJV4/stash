import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from builders import LATER, a_capture, an_item, an_outcome, stored_item
from fakes.store_factories import opened
from migration_sets import (
    INIT_SCRIPT,
    LIFECYCLE_SCRIPT,
    STEPS_SCRIPT,
    packaged_scripts,
    write_migrations,
)

from stash.domain import Item, Stage
from stash.store.sqlite import SqliteStore

TRIGGER_MIGRATION = """
CREATE TRIGGER refuse_forbidden_capture BEFORE INSERT ON captures WHEN new.text = 'forbidden'
BEGIN SELECT RAISE(ABORT, 'forbidden capture'); END;

CREATE TRIGGER refuse_forbidden_item BEFORE INSERT ON items WHEN new.title = 'forbidden'
BEGIN SELECT RAISE(ABORT, 'forbidden item'); END;

CREATE TRIGGER refuse_forbidden_outcome BEFORE INSERT ON outcomes WHEN new.notes = 'forbidden'
BEGIN SELECT RAISE(ABORT, 'forbidden outcome'); END;
"""


def with_trigger_migration(directory: Path) -> Path:
    return write_migrations(
        directory,
        {
            **packaged_scripts(INIT_SCRIPT, LIFECYCLE_SCRIPT, STEPS_SCRIPT),
            "0004_triggers.sql": TRIGGER_MIGRATION,
        },
    )


@pytest.mark.integration
def test_captures_survive_reopening_the_database_file(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as first:
        first.add_capture(a_capture())

    # Execute
    with opened(path) as second:
        found = second.get_capture("c1")

    # Assert
    assert found == a_capture()


@pytest.mark.integration
def test_items_survive_reopening_the_database_file(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as first:
        first.add_capture(a_capture())
        first.save_item(an_item())

    # Execute
    with opened(path) as second:
        found = second.get_item("i1")

    # Assert
    assert found == an_item()


@pytest.mark.integration
def test_settings_survive_reopening_the_database_file(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as first:
        first.put_setting("key", "value")

    # Execute
    with opened(path) as second:
        found = second.get_setting("key")

    # Assert
    assert found == "value"


@pytest.mark.integration
def test_the_database_file_is_in_wal_journal_mode(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"

    # Execute
    with opened(path), closing(sqlite3.connect(path)) as raw:
        journal_mode = raw.execute("PRAGMA journal_mode").fetchone()[0]

    # Assert
    assert journal_mode == "wal"


@pytest.mark.integration
def test_a_backup_opens_as_a_store_with_the_same_data(tmp_path: Path) -> None:
    # Setup
    with opened(tmp_path / "stash.db") as source:
        source.add_capture(a_capture())
        source.save_item(an_item())
        source.backup_to(tmp_path / "backup.db")

    # Execute
    with opened(tmp_path / "backup.db") as copy:
        found = (copy.get_capture("c1"), copy.get_item("i1"))

    # Assert
    assert found == (a_capture(), an_item())


@pytest.mark.integration
def test_a_backup_does_not_change_the_source_database(tmp_path: Path) -> None:
    # Setup
    with opened(tmp_path / "stash.db") as source:
        source.add_capture(a_capture())

        # Execute
        source.backup_to(tmp_path / "backup.db")

        # Assert
        assert source.get_capture("c1") == a_capture()


@pytest.mark.integration
def test_a_capture_refused_by_another_constraint_is_not_reported_as_a_duplicate_id(
    tmp_path: Path,
) -> None:
    # Setup
    migrations = with_trigger_migration(tmp_path / "migrations")
    with opened(tmp_path / "stash.db", migrations) as store, pytest.raises(sqlite3.IntegrityError):
        # Execute / Assert
        store.add_capture(a_capture(text="forbidden"))


@pytest.mark.integration
def test_an_item_refused_by_another_constraint_is_not_reported_as_an_unknown_capture(
    tmp_path: Path,
) -> None:
    # Setup
    migrations = with_trigger_migration(tmp_path / "migrations")
    with opened(tmp_path / "stash.db", migrations) as store:
        store.add_capture(a_capture())

        # Execute / Assert
        with pytest.raises(sqlite3.IntegrityError):
            store.save_item(an_item(title="forbidden"))


@contextmanager
def store_holding_a_doing_item(tmp_path: Path) -> Iterator[tuple[SqliteStore, Item]]:
    migrations = with_trigger_migration(tmp_path / "migrations")
    with opened(tmp_path / "stash.db", migrations) as store:
        yield store, stored_item(store, stage=Stage.DOING)


@pytest.mark.integration
def test_a_completion_whose_outcome_is_refused_leaves_the_item_unchanged(tmp_path: Path) -> None:
    # Setup
    with store_holding_a_doing_item(tmp_path) as (store, item):
        # Execute
        with pytest.raises(sqlite3.IntegrityError, match="forbidden outcome"):
            store.record_completion(
                item.completed(LATER), an_outcome(notes="forbidden"), replacing=item
            )

        # Assert
        assert store.get_item("i1") == item


@pytest.mark.integration
def test_a_completion_whose_outcome_is_refused_stores_no_outcome(tmp_path: Path) -> None:
    # Setup
    with store_holding_a_doing_item(tmp_path) as (store, item):
        # Execute
        with pytest.raises(sqlite3.IntegrityError, match="forbidden outcome"):
            store.record_completion(
                item.completed(LATER), an_outcome(notes="forbidden"), replacing=item
            )

        # Assert
        assert store.outcomes_for("i1") == []
