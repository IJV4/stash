from pathlib import Path

from config_toml import a_toml, load, load_message, with_key


def test_configured_absolute_data_dir_is_used_as_is(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='data_dir = "/srv/stash"'))

    # Assert
    assert config.data_dir == Path("/srv/stash")


def test_configured_data_dir_expands_a_leading_tilde_slash_with_home(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='data_dir = "~/notes/stash"'))

    # Assert
    assert config.data_dir == Path("/home/u/notes/stash")


def test_configured_data_dir_expands_a_lone_tilde_with_home(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='data_dir = "~"'))

    # Assert
    assert config.data_dir == Path("/home/u")


def test_tilde_data_dir_without_home_is_a_config_error(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(top='data_dir = "~/stash"'), {})

    # Assert
    assert "HOME" in message


def test_other_users_tilde_data_dir_is_rejected_as_not_absolute(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(top='data_dir = "~bob/stash"'))

    # Assert
    assert "data_dir" in message


def test_relative_data_dir_is_a_config_error(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(top='data_dir = "stash"'))

    # Assert
    assert "data_dir" in message


def test_default_data_dir_falls_back_to_home_local_share(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.data_dir == Path("/home/u/.local/share/stash")


def test_default_data_dir_prefers_xdg_data_home(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_key(XDG_DATA_HOME="/xdg"))

    # Assert
    assert config.data_dir == Path("/xdg/stash")


def test_blank_xdg_data_home_is_ignored(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_key(XDG_DATA_HOME=" "))

    # Assert
    assert config.data_dir == Path("/home/u/.local/share/stash")


def test_default_data_dir_with_xdg_does_not_need_home(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), {"XDG_DATA_HOME": "/xdg"})

    # Assert
    assert config.data_dir == Path("/xdg/stash")


def test_default_data_dir_without_xdg_or_home_is_a_config_error(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(), {})

    # Assert
    assert "HOME" in message


def test_configured_data_dir_wins_over_xdg_data_home(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='data_dir = "/srv/stash"'), with_key(XDG_DATA_HOME="/xdg"))

    # Assert
    assert config.data_dir == Path("/srv/stash")


def test_db_path_lives_inside_the_data_dir(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='data_dir = "/srv/stash"'))

    # Assert
    assert config.db_path == Path("/srv/stash/stash.db")
