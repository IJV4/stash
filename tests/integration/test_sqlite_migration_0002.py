import json
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from builders import BASE, a_capture, a_source, an_item, an_item_at, minutes_after
from fakes.store_factories import opened
from migration_sets import INIT_SCRIPT, LIFECYCLE_SCRIPT, packaged_scripts, write_migrations

from stash.domain import Item, ItemType, Stage, utc_text

LIFECYCLE_SCHEMA_VERSION = 2
PLAN_ONE_ITEM_COLUMNS = (
    "id, capture_id, item_type, title, stage, source_url, note, details, tags, people, "
    "date, created_at, updated_at"
)


def insert_plan_one_item(connection: sqlite3.Connection, item: Item) -> None:
    connection.execute(
        f"INSERT INTO items ({PLAN_ONE_ITEM_COLUMNS}) VALUES ({', '.join('?' * 13)})",
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
        ),
    )
    connection.commit()


def plan_one_items() -> list[Item]:
    return [
        an_item(id="i1", title="Inbox thing", created_at=minutes_after(1)),
        an_item_at(Stage.PLANNED, id="i2", title="Planned thing", created_at=minutes_after(2)),
        an_item_at(Stage.DONE, id="i3", title="Done thing", created_at=minutes_after(3)),
        an_item_at(Stage.DROPPED, id="i4", title="Dropped thing", created_at=minutes_after(4)),
        an_item(
            id="i5",
            title="Everything set",
            item_type=ItemType.RECIPE,
            stage=Stage.PLANNED,
            source_url="https://example.com/ramen",
            note="Bring cash",
            details={"city": "Tokyo"},
            tags=("food", "ramen"),
            people=("Aiko",),
            date=date(2026, 12, 24),
            created_at=minutes_after(5),
        ),
    ]


def plan_one_database(tmp_path: Path) -> Path:
    path = tmp_path / "stash.db"
    plan_one = write_migrations(tmp_path / "plan-one", packaged_scripts(INIT_SCRIPT))
    with opened(path, plan_one) as store:
        store.add_capture(a_capture())
        store.add_capture(a_capture(id="c2", source=a_source("m2"), received_at=BASE))
    with closing(sqlite3.connect(path)) as raw:
        for item in plan_one_items():
            insert_plan_one_item(raw, item)
    return path


def schema_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


@pytest.mark.integration
def test_a_plan_one_database_migrates_to_the_lifecycle_schema_version(tmp_path: Path) -> None:
    # Setup
    path = plan_one_database(tmp_path)
    lifecycle = write_migrations(
        tmp_path / "lifecycle", packaged_scripts(INIT_SCRIPT, LIFECYCLE_SCRIPT)
    )

    # Execute
    with opened(path, lifecycle):
        pass

    # Assert
    assert schema_version(path) == LIFECYCLE_SCHEMA_VERSION


@pytest.mark.integration
def test_a_plan_one_database_keeps_every_capture_after_migrating(tmp_path: Path) -> None:
    # Setup
    path = plan_one_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = (store.get_capture("c1"), store.get_capture("c2"))

    # Assert
    assert found == (a_capture(), a_capture(id="c2", source=a_source("m2")))


@pytest.mark.integration
def test_a_plan_one_database_keeps_every_item_unkept_ungrouped_and_without_drop_reason(
    tmp_path: Path,
) -> None:
    # Setup
    path = plan_one_database(tmp_path)

    # Execute
    with opened(path) as store:
        found = [store.get_item(item.id) for item in plan_one_items()]

    # Assert
    assert found == plan_one_items()
