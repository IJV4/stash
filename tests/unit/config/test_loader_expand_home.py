from pathlib import Path

import pytest

from stash.config import ConfigError
from stash.config.loader import expand_home

HOME = "/home/u"


def test_a_leading_tilde_slash_is_replaced_by_home() -> None:
    # Execute
    path = expand_home("~/notes/stash.toml", {"HOME": HOME})

    # Assert
    assert path == Path("/home/u/notes/stash.toml")


def test_a_lone_tilde_is_home() -> None:
    # Execute
    path = expand_home("~", {"HOME": HOME})

    # Assert
    assert path == Path(HOME)


def test_an_absolute_path_is_returned_as_it_is() -> None:
    # Execute
    path = expand_home("/etc/stash.toml", {"HOME": HOME})

    # Assert
    assert path == Path("/etc/stash.toml")


def test_an_absolute_path_needs_no_home() -> None:
    # Execute
    path = expand_home("/etc/stash.toml", {})

    # Assert
    assert path == Path("/etc/stash.toml")


def test_another_users_tilde_path_is_not_expanded() -> None:
    # Execute
    path = expand_home("~bob/stash.toml", {"HOME": HOME})

    # Assert
    assert path == Path("~bob/stash.toml")


def test_whitespace_around_home_is_ignored() -> None:
    # Execute
    path = expand_home("~/x", {"HOME": f"  {HOME} "})

    # Assert
    assert path == Path("/home/u/x")


@pytest.mark.parametrize(
    "environment", [{}, {"HOME": ""}, {"HOME": "  "}], ids=["unset", "empty", "blank"]
)
def test_a_tilde_path_without_a_usable_home_is_a_config_error(
    environment: dict[str, str],
) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="HOME"):
        expand_home("~/x", environment)
