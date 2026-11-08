from contextlib import ExitStack
from pathlib import Path

import pytest
from config_builders import a_stash_config

from stash.app.database import open_database
from stash.config import ConfigError


def test_a_file_that_is_not_a_database_is_a_config_error(tmp_path: Path) -> None:
    # Setup
    (tmp_path / "stash.db").write_bytes(b"this is not sqlite" * 100)

    # Execute / Assert
    with pytest.raises(ConfigError, match="cannot open the database"), ExitStack() as resources:
        open_database(a_stash_config(data_dir=tmp_path), resources)
