import sqlite3
from contextlib import closing
from importlib.resources import files
from pathlib import Path

import pytest
from fakes.store_factories import opened
from migration_sets import packaged_init_script, write_migrations
from threads import run_concurrently

from stash.store._migrate import apply_migrations
from stash.store.sqlite import SqliteStore

CREATE_T = "CREATE TABLE t (n INTEGER);"
BROKEN = "CREATE TABLE half (n INTEGER); INSERT INTO missing VALUES (1);"
CONCURRENT_OPENERS = 4
SLOW_FILL = (
    "CREATE TABLE filler (n INTEGER);"
    "WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c WHERE n < 300000) "
    "INSERT INTO filler SELECT n FROM c;"
)
UNTERMINATED_TRIGGER = (
    "CREATE TABLE t (n INTEGER);CREATE TRIGGER keep AFTER INSERT ON t BEGIN SELECT 1;"
)
FULLWIDTH_NUMBERED = "\uff10\uff10\uff10\uff12_second.sql"


def schema_version(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection:
        version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


def table_names(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def packaged_migration_count() -> int:
    packaged = files("stash.store") / "migrations"
    return sum(1 for entry in packaged.iterdir() if entry.name.endswith(".sql"))


@pytest.mark.integration
def test_a_new_database_records_the_newest_packaged_schema_version(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"

    # Execute
    SqliteStore(path).close()

    # Assert
    assert schema_version(path) == packaged_migration_count()


@pytest.mark.integration
def test_reopening_does_not_rerun_migrations_over_existing_data(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as first:
        first.put_setting("sentinel", "kept")

    # Execute
    with opened(path) as second:
        found = second.get_setting("sentinel")

    # Assert
    assert found == "kept"


@pytest.mark.integration
def test_opening_a_database_from_a_newer_schema_raises_value_error(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with closing(sqlite3.connect(path)) as raw:
        raw.execute("PRAGMA user_version = 99")

    # Execute / Assert
    with pytest.raises(ValueError, match="99"):
        SqliteStore(path)


@pytest.mark.integration
def test_migrations_run_in_numeric_order(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations",
        {
            "0003_third.sql": "INSERT INTO t VALUES (2);",
            "0002_second.sql": "INSERT INTO t VALUES (1);",
            "0001_first.sql": CREATE_T,
        },
    )

    # Execute
    SqliteStore(path, migrations).close()
    with closing(sqlite3.connect(path)) as raw:
        rows = raw.execute("SELECT n FROM t ORDER BY rowid").fetchall()

    # Assert
    assert rows == [(1,), (2,)]


@pytest.mark.integration
def test_applied_migrations_are_not_run_again(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(tmp_path / "migrations", {"0001_first.sql": CREATE_T})
    SqliteStore(path, migrations).close()

    # Execute
    SqliteStore(path, migrations).close()

    # Assert
    assert schema_version(path) == 1


@pytest.mark.integration
def test_only_the_missing_migrations_run_on_an_older_database(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    first = write_migrations(tmp_path / "first", {"0001_first.sql": CREATE_T})
    SqliteStore(path, first).close()
    both = write_migrations(
        tmp_path / "both",
        {"0001_first.sql": CREATE_T, "0002_second.sql": "INSERT INTO t VALUES (7);"},
    )

    # Execute
    SqliteStore(path, both).close()

    # Assert
    assert schema_version(path) == 2


@pytest.mark.integration
def test_a_failing_migration_leaves_the_schema_version_unchanged(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_first.sql": CREATE_T, "0002_broken.sql": BROKEN}
    )

    # Execute
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(path, migrations)

    # Assert
    assert schema_version(path) == 1


@pytest.mark.integration
def test_a_failing_migration_leaves_no_partial_schema_behind(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_first.sql": CREATE_T, "0002_broken.sql": BROKEN}
    )
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(path, migrations)

    # Execute
    tables = table_names(path)

    # Assert
    assert tables == {"t"}


@pytest.mark.integration
def test_a_failing_migration_leaves_no_transaction_open_on_a_long_lived_connection(
    tmp_path: Path,
) -> None:
    # Setup
    migrations = write_migrations(tmp_path / "migrations", {"0001_broken.sql": BROKEN})
    with closing(sqlite3.connect(tmp_path / "stash.db", isolation_level=None)) as connection:
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(connection, migrations)

        # Execute
        still_open = connection.in_transaction

    # Assert
    assert still_open is False


@pytest.mark.integration
def test_a_failed_open_closes_its_connection_to_the_database_file(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(tmp_path / "migrations", {"0001_broken.sql": BROKEN})
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(path, migrations)

    # Execute
    leftovers = sorted(entry.name for entry in tmp_path.glob("stash.db-*"))

    # Assert
    assert leftovers == []


@pytest.mark.integration
def test_a_migration_ending_in_an_unterminated_statement_raises_operational_error(
    tmp_path: Path,
) -> None:
    # Setup
    migrations = write_migrations(tmp_path / "migrations", {"0001_first.sql": UNTERMINATED_TRIGGER})

    # Execute / Assert
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(tmp_path / "stash.db", migrations)


@pytest.mark.integration
def test_a_migration_ending_in_an_unterminated_statement_leaves_the_schema_version_unchanged(
    tmp_path: Path,
) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(tmp_path / "migrations", {"0001_first.sql": UNTERMINATED_TRIGGER})
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(path, migrations)

    # Execute
    version = schema_version(path)

    # Assert
    assert version == 0


@pytest.mark.integration
def test_a_migration_ending_in_an_unterminated_statement_leaves_no_partial_schema_behind(
    tmp_path: Path,
) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(tmp_path / "migrations", {"0001_first.sql": UNTERMINATED_TRIGGER})
    with pytest.raises(sqlite3.OperationalError):
        SqliteStore(path, migrations)

    # Execute
    tables = table_names(path)

    # Assert
    assert tables == set()


@pytest.mark.integration
def test_a_semicolon_inside_a_string_literal_does_not_split_the_statement(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations",
        {"0001_first.sql": "CREATE TABLE t (n TEXT); INSERT INTO t VALUES ('a;b');"},
    )
    SqliteStore(path, migrations).close()

    # Execute
    with closing(sqlite3.connect(path)) as raw:
        rows = raw.execute("SELECT n FROM t").fetchall()

    # Assert
    assert rows == [("a;b",)]


@pytest.mark.integration
def test_a_semicolon_inside_a_comment_does_not_split_the_statement(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations",
        {"0001_first.sql": "CREATE TABLE t (n INTEGER);\n-- one; two\nINSERT INTO t VALUES (1);"},
    )
    SqliteStore(path, migrations).close()

    # Execute
    with closing(sqlite3.connect(path)) as raw:
        rows = raw.execute("SELECT n FROM t").fetchall()

    # Assert
    assert rows == [(1,)]


@pytest.mark.integration
def test_a_comment_after_the_last_statement_is_harmless(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_first.sql": f"{CREATE_T}\n-- end of file\n"}
    )

    # Execute
    SqliteStore(path, migrations).close()

    # Assert
    assert schema_version(path) == 1


@pytest.mark.integration
def test_file_names_with_non_ascii_digits_are_not_migrations(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations",
        {"0001_first.sql": CREATE_T, FULLWIDTH_NUMBERED: "INSERT INTO t VALUES (1);"},
    )

    # Execute
    SqliteStore(path, migrations).close()

    # Assert
    assert schema_version(path) == 1


@pytest.mark.integration
def test_duplicate_migration_numbers_raise_value_error(tmp_path: Path) -> None:
    # Setup
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_first.sql": CREATE_T, "0001_other.sql": CREATE_T}
    )

    # Execute / Assert
    with pytest.raises(ValueError, match="duplicate"):
        SqliteStore(tmp_path / "stash.db", migrations)


@pytest.mark.integration
def test_a_gap_in_migration_numbers_raises_value_error(tmp_path: Path) -> None:
    # Setup
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_first.sql": CREATE_T, "0003_third.sql": CREATE_T}
    )

    # Execute / Assert
    with pytest.raises(ValueError, match="contiguous"):
        SqliteStore(tmp_path / "stash.db", migrations)


@pytest.mark.integration
def test_an_empty_migration_set_raises_value_error(tmp_path: Path) -> None:
    # Setup
    migrations = write_migrations(tmp_path / "migrations", {})

    # Execute / Assert
    with pytest.raises(ValueError, match="no migrations"):
        SqliteStore(tmp_path / "stash.db", migrations)


@pytest.mark.integration
def test_concurrent_first_opens_of_the_same_file_all_succeed(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    migrations = write_migrations(
        tmp_path / "migrations", {"0001_init.sql": f"{packaged_init_script()}\n{SLOW_FILL}"}
    )
    seen: list[str | None] = []

    def open_and_use(worker: int) -> None:
        with opened(path, migrations) as store:
            store.put_setting(f"worker-{worker}", "ready")
            seen.append(store.get_setting(f"worker-{worker}"))

    # Execute
    errors = run_concurrently(CONCURRENT_OPENERS, open_and_use)

    # Assert
    assert (errors, seen) == ([], ["ready"] * CONCURRENT_OPENERS)


@pytest.mark.integration
def test_opening_an_up_to_date_database_does_not_need_the_write_lock(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    SqliteStore(path).close()
    with closing(sqlite3.connect(path, isolation_level=None)) as writer:
        writer.execute("BEGIN IMMEDIATE")

        # Execute
        with opened(path) as store:
            found = store.get_setting("missing")

    # Assert
    assert found is None
