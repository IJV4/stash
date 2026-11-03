from pathlib import Path

import pytest
from stash.cli.config_path import config_path

from stash.config import ConfigError

HOME_ENV = {"HOME": "/home/u"}


def test_the_config_option_wins_over_the_environment_and_the_default() -> None:
    # Setup
    env = {**HOME_ENV, "STASH_CONFIG": "/etc/stash.toml"}

    # Execute
    path = config_path("/tmp/mine.toml", env)

    # Assert
    assert path == Path("/tmp/mine.toml")


def test_the_stash_config_variable_wins_over_the_default() -> None:
    # Setup
    env = {**HOME_ENV, "STASH_CONFIG": "/etc/stash.toml"}

    # Execute
    path = config_path(None, env)

    # Assert
    assert path == Path("/etc/stash.toml")


def test_without_an_option_or_variable_the_file_under_home_is_used() -> None:
    # Execute
    path = config_path(None, HOME_ENV)

    # Assert
    assert path == Path("/home/u/.config/stash/stash.toml")


def test_an_empty_stash_config_variable_counts_as_unset() -> None:
    # Execute
    path = config_path(None, {**HOME_ENV, "STASH_CONFIG": ""})

    # Assert
    assert path == Path("/home/u/.config/stash/stash.toml")


def test_without_an_option_variable_or_home_the_config_cannot_be_located() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="--config"):
        config_path(None, {})
