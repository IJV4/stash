import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from builders import BASE, a_capture, an_item, an_item_at, an_outcome, minutes_after
from fakes.store_factories import opened
from migration_sets import INIT_SCRIPT, LIFECYCLE_SCRIPT, packaged_scripts, write_migrations
from step_builders import a_nudge, a_step

from stash.domain import Item, Outcome, Stage, utc_text

LIFECYCLE_SCHEMA_VERSION = 2
STEPS_SCHEMA_VERSION = 3
LIFECYCLE_ITEM_COLUMNS = (
    "id, capture_id, item_type, title, stage, source_url, note, details, tags, people, "
    "date, created_at, updated_at, kept, parent_id, drop_reason"
)
INSERT_LIFECYCLE_ITEM = (
    f"INSERT INTO items ({LIFECYCLE_ITEM_COLUMNS}) VALUES ({', '.join('?' * 16)})"
)
INSERT_LIFECYCLE_OUTCOME = (
    "INSERT INTO outcomes (id, item_id, completed_on, rating, notes, takeaways, recorded_at, "
    "edited_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
DUPLICATE_NUDGE_ROW = ("step", "s1", "2026-11-02T21:00:00.000000+00:00", "2026-11-03T08:00:00")


def lifecycle_items() -> list[Item]:
    return [
        an_item(id="i1", title="Inbox thing", created_at=minutes_after(1)),
        an_item_at(
            Stage.DOING, id="p1", title="Japan trip", kept=False, created_at=minutes_after(2)
        ),
        an_item_at(
            Stage.WANT_TO, id="i3", title="Child", parent_id="p1", created_at=minutes_after(3)
        ),
        an_item_at(
            Stage.DROPPED,
            id="i4",
            title="Dropped thing",
            drop_reason="changed my mind",
            created_at=minutes_after(4),
        ),
        an_item_at(Stage.DONE, id="i5", title="Kept thing", kept=True, created_at=minutes_after(5)),
    ]


def insert_lifecycle_item(connection: sqlite3.Connection, item: Item) -> None:
    connection.execute(
        INSERT_LIFECYCLE_ITEM,
        (
            item.id,
            item.capture_id,
            item.item_type.value,
            item.title,
            item.stage.value,
            item.source_url,
            item.note,
            json.dumps(dict(item.details), ensure_ascii=False),
            json.dumps(item.tags, ensure_ascii=False),
            json.dumps(item.people, ensure_ascii=False),
            None if item.date is None else item.date.isoformat(),
            utc_text(item.created_at),
            utc_text(item.updated_at),
            int(item.kept),
            item.parent_id,
            item.drop_reason,
        ),
    )


def insert_lifecycle_outcome(connection: sqlite3.Connection, outcome: Outcome) -> None:
    connection.execute(
        INSERT_LIFECYCLE_OUTCOME,
        (
            outcome.id,
            outcome.item_id,
            outcome.completed_on.isoformat(),
            outcome.rating,
            outcome.notes,
            json.dumps(outcome.takeaways, ensure_ascii=False),
            utc_text(outcome.recorded_at),
            None if outcome.edited_at is None else utc_text(outcome.edited_at),
        ),
    )


def lifecycle_database(tmp_path: Path) -> Path:
    path = tmp_path / "stash.db"
    lifecycle = write_migrations(
        tmp_path / "lifecycle", packaged_scripts(INIT_SCRIPT, LIFECYCLE_SCRIPT)
    )
    with opened(path, lifecycle) as store:
        store.add_capture(a_capture())
    with closing(sqlite3.connect(path)) as raw:
        for item in lifecycle_items():
            insert_lifecycle_item(raw, item)
        insert_lifecycle_outcome(raw, an_outcome(item_id="i5"))
        raw.commit()
    assert schema_version(path) == LIFECYCLE_SCHEMA_VERSION
    return path


def schema_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


@pytest.mark.integration
def test_a_lifecycle_database_migrates_to_the_steps_schema_version(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)

    # Execute
    with opened(path):
        pass

    # Assert
    assert schema_version(path) == STEPS_SCHEMA_VERSION


@pytest.mark.integration
def test_a_lifecycle_database_keeps_its_capture_after_migrating(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = store.get_capture("c1")

    # Assert
    assert found == a_capture()


@pytest.mark.integration
def test_a_lifecycle_database_keeps_every_item_with_no_cool_off_date(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = [store.get_item(item.id) for item in lifecycle_items()]

    # Assert
    assert found == lifecycle_items()


@pytest.mark.integration
def test_a_lifecycle_database_keeps_its_outcome_after_migrating(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = store.outcomes_for("i5")

    # Assert
    assert found == [an_outcome(item_id="i5")]


@pytest.mark.integration
def test_a_migrated_database_stores_and_returns_steps(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)
    step = a_step(item_id="i1")

    # Execute
    with opened(path) as store:
        store.save_steps("i1", [step])
        found = store.steps_for("i1")

    # Assert
    assert found == [step]


@pytest.mark.integration
def test_a_migrated_database_remembers_a_sent_nudge_after_reopening(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)
    with opened(path) as store:
        store.record_all_sent([a_nudge()], BASE)

    # Execute
    with opened(path) as reopened:
        sent = reopened.was_sent(a_nudge().key)

    # Assert
    assert sent is True


@pytest.mark.integration
def test_deleting_an_item_in_sqlite_deletes_its_steps_through_the_foreign_key(
    tmp_path: Path,
) -> None:
    # Setup
    path = lifecycle_database(tmp_path)
    with opened(path) as store:
        store.save_steps("i1", [a_step(item_id="i1")])

        # Execute
        store.delete_item("i1")

        # Assert
        assert store.get_step("s1") is None


@pytest.mark.integration
def test_a_second_ledger_row_for_the_same_key_is_refused_by_the_database(tmp_path: Path) -> None:
    # Setup
    path = lifecycle_database(tmp_path)
    with opened(path), closing(sqlite3.connect(path)) as raw:
        raw.execute("INSERT INTO sent_nudges VALUES (?, ?, ?, ?)", DUPLICATE_NUDGE_ROW)

        # Execute / Assert
        with pytest.raises(sqlite3.IntegrityError):
            raw.execute("INSERT INTO sent_nudges VALUES (?, ?, ?, ?)", DUPLICATE_NUDGE_ROW)
