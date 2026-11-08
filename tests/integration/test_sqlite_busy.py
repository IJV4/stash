import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from builders import LATER, an_item, an_item_at, an_outcome
from fakes.store_factories import opened
from step_builders import a_step
from threads import run_in_thread

from stash.domain import ItemType, Stage
from stash.store import StoreBusyError
from stash.store._transaction import immediate_transaction
from stash.store.sqlite import BUSY_TIMEOUT, SqliteStore

SHORT_WAIT = timedelta(milliseconds=100)
PROMPT_SECONDS = 1.0
FAR_SHORTER_THAN_THE_DEFAULT = timedelta(seconds=2)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "stash.db"
    with opened(path):
        pass
    return path


@pytest.fixture
def rival(database: Path) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(database, isolation_level=None)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        yield connection


@pytest.fixture
def impatient_store(database: Path, rival: sqlite3.Connection) -> Iterator[SqliteStore]:
    store = SqliteStore(database, busy_timeout=SHORT_WAIT)
    try:
        yield store
    finally:
        store.close()


@pytest.fixture
def plain_file(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(tmp_path / "plain.db", isolation_level=None)) as connection:
        yield connection


def an_impatient_connection(database: Path) -> sqlite3.Connection:
    return sqlite3.connect(database, isolation_level=None, timeout=SHORT_WAIT.total_seconds())


@pytest.mark.integration
def test_the_default_wait_for_the_write_lock_is_five_seconds() -> None:
    # Assert
    assert timedelta(seconds=5) == BUSY_TIMEOUT


@pytest.mark.integration
def test_a_transaction_that_cannot_get_the_write_lock_raises_store_busy(
    database: Path, rival: sqlite3.Connection
) -> None:
    # Execute / Assert
    with (
        closing(an_impatient_connection(database)) as waiting,
        pytest.raises(StoreBusyError),
        immediate_transaction(waiting),
    ):
        pass


@pytest.mark.integration
def test_the_store_busy_error_is_chained_from_the_busy_error_of_sqlite(
    database: Path, rival: sqlite3.Connection
) -> None:
    # Execute
    with (
        closing(an_impatient_connection(database)) as waiting,
        pytest.raises(StoreBusyError) as caught,
        immediate_transaction(waiting),
    ):
        pass

    # Assert
    assert getattr(caught.value.__cause__, "sqlite_errorname", None) == "SQLITE_BUSY"


@pytest.mark.integration
def test_the_store_busy_error_says_that_another_writer_held_the_stash_for_the_whole_wait(
    database: Path, rival: sqlite3.Connection
) -> None:
    # Execute
    with (
        closing(an_impatient_connection(database)) as waiting,
        pytest.raises(StoreBusyError) as caught,
        immediate_transaction(waiting),
    ):
        pass

    # Assert
    assert "another writer" in str(caught.value)


@pytest.mark.integration
def test_a_begin_that_fails_for_another_reason_is_not_reported_as_busy(
    plain_file: sqlite3.Connection,
) -> None:
    # Setup
    plain_file.execute("BEGIN")

    # Execute / Assert
    with (
        pytest.raises(sqlite3.OperationalError, match="within a transaction"),
        immediate_transaction(plain_file),
    ):
        pass


@pytest.mark.integration
def test_a_store_write_gives_up_with_store_busy_when_another_connection_holds_the_write_lock(
    impatient_store: SqliteStore,
) -> None:
    # Execute / Assert
    with pytest.raises(StoreBusyError):
        impatient_store.save_step(a_step())


@pytest.mark.integration
def test_a_store_write_waits_at_least_the_busy_timeout_before_giving_up(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    started = time.perf_counter()
    with pytest.raises(StoreBusyError):
        impatient_store.save_step(a_step())

    # Execute
    waited = timedelta(seconds=time.perf_counter() - started)

    # Assert
    assert waited >= SHORT_WAIT


@pytest.mark.integration
def test_a_store_write_gives_up_after_the_busy_timeout_it_was_given_not_the_default(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    started = time.perf_counter()
    with pytest.raises(StoreBusyError):
        impatient_store.save_step(a_step())

    # Execute
    waited = timedelta(seconds=time.perf_counter() - started)

    # Assert
    assert waited < FAR_SHORTER_THAN_THE_DEFAULT


@pytest.mark.integration
def test_another_thread_can_use_the_store_right_after_a_write_gave_up(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    with pytest.raises(StoreBusyError):
        impatient_store.save_step(a_step())

    # Execute
    setting = run_in_thread(lambda: impatient_store.get_setting("greeting"), PROMPT_SECONDS)

    # Assert
    assert setting is None


@pytest.mark.integration
def test_the_store_writes_again_once_the_rival_lets_go(
    impatient_store: SqliteStore, rival: sqlite3.Connection
) -> None:
    # Setup
    with pytest.raises(StoreBusyError):
        impatient_store.save_step(a_step())
    rival.execute("ROLLBACK")

    # Execute
    impatient_store.put_setting("greeting", "hello")

    # Assert
    assert impatient_store.get_setting("greeting") == "hello"


@pytest.mark.integration
def test_an_item_update_gives_up_with_store_busy_when_another_connection_holds_the_write_lock(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    read = an_item()

    # Execute / Assert
    with pytest.raises(StoreBusyError):
        impatient_store.update_item(read.retyped(ItemType.BOOK, LATER))


@pytest.mark.integration
def test_a_completion_gives_up_with_store_busy_when_another_connection_holds_the_write_lock(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    read = an_item_at(Stage.DOING)

    # Execute / Assert
    with pytest.raises(StoreBusyError):
        impatient_store.record_completion(read.completed(LATER), an_outcome())


@pytest.mark.integration
def test_a_grouping_gives_up_with_store_busy_before_it_checks_anything_when_the_write_lock_is_held(
    impatient_store: SqliteStore,
) -> None:
    # Setup
    read = an_item()

    # Execute / Assert
    with pytest.raises(StoreBusyError):
        impatient_store.group_item(replace(read, parent_id="p1", updated_at=LATER))
