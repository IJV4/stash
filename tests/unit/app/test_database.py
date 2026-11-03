import sqlite3
from contextlib import ExitStack
from pathlib import Path

import pytest
from config_builders import a_stash_config

from stash.app.database import open_database
from stash.config import ConfigError


def test_opening_creates_the_data_directory_and_the_database_file(tmp_path: Path) -> None:
    # Setup
    config = a_stash_config(data_dir=tmp_path / "deep" / "data")

    # Execute
    with ExitStack() as resources:
        open_database(config, resources)

    # Assert
    assert config.db_path.is_file()


def test_the_database_is_closed_when_the_resources_are_closed(tmp_path: Path) -> None:
    # Setup
    resources = ExitStack()
    store = open_database(a_stash_config(data_dir=tmp_path), resources)

    # Execute
    resources.close()

    # Assert
    with pytest.raises(sqlite3.ProgrammingError):
        store.list_items()


def test_a_data_directory_that_cannot_be_created_is_a_config_error_naming_the_database(
    tmp_path: Path,
) -> None:
    # Setup
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    config = a_stash_config(data_dir=blocker / "data")

    # Execute
    with pytest.raises(ConfigError) as failure, ExitStack() as resources:
        open_database(config, resources)

    # Assert
    assert str(failure.value).startswith(f"cannot open the database at {config.db_path}: ")


def test_a_file_that_is_not_a_database_is_a_config_error(tmp_path: Path) -> None:
    # Setup
    (tmp_path / "stash.db").write_bytes(b"this is not sqlite" * 100)

    # Execute / Assert
    with pytest.raises(ConfigError, match="cannot open the database"), ExitStack() as resources:
        open_database(a_stash_config(data_dir=tmp_path), resources)
