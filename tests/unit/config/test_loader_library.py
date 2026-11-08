from pathlib import Path

import pytest
from config_toml import a_toml, load, load_message, with_key

from stash.config import LibraryConfig

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "deploy" / "stash.toml.example"
LIBRARY_BLOCK_LINES = ["# [library]", '# bind = "0.0.0.0"', "# port = 8765"]
TOKEN = "Ab3-._~Ab3-._~Ab3-._~Ab3-"
TOKEN_VAR = "STASH_LIBRARY_TOKEN"


def with_library(body: str) -> str:
    return a_toml(top=f"[library]\n{body}\n")


def with_token(value: str) -> dict[str, str]:
    return with_key(**{TOKEN_VAR: value})


def test_without_a_library_table_the_server_binds_every_interface_on_port_8765(
    tmp_path: Path,
) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert (config.library.bind, config.library.port) == ("0.0.0.0", 8765)


def test_bind_and_port_are_read_from_the_library_table(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_library('bind = "192.168.1.5"\nport = 9000'))

    # Assert
    assert config.library == LibraryConfig(bind="192.168.1.5", port=9000, token=None)


@pytest.mark.parametrize("port", [1, 65535])
def test_the_lowest_and_highest_valid_ports_are_accepted(tmp_path: Path, port: int) -> None:
    # Execute
    config = load(tmp_path, with_library(f"port = {port}"))

    # Assert
    assert config.library.port == port


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_a_port_outside_1_to_65535_is_refused(tmp_path: Path, port: int) -> None:
    # Execute
    refusal = load_message(tmp_path, with_library(f"port = {port}"))

    # Assert
    assert "library.port must be between 1 and 65535" in refusal


def test_a_port_that_is_not_an_integer_is_refused(tmp_path: Path) -> None:
    # Execute
    refusal = load_message(tmp_path, with_library('port = "8765"'))

    # Assert
    assert "library.port must be an integer" in refusal


def test_an_unknown_key_in_the_library_table_is_refused(tmp_path: Path) -> None:
    # Execute
    refusal = load_message(tmp_path, with_library("prot = 9000"))

    # Assert
    assert "library.prot" in refusal


def test_the_token_is_read_from_the_environment(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_token(TOKEN))

    # Assert
    assert config.library.token == TOKEN


def test_the_token_is_stripped_of_surrounding_whitespace(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_token(f"  {TOKEN}\n"))

    # Assert
    assert config.library.token == TOKEN


@pytest.mark.parametrize("value", [None, "", "   "])
def test_an_absent_or_blank_token_means_no_token(tmp_path: Path, value: str | None) -> None:
    # Setup
    env = with_key() if value is None else with_token(value)

    # Execute
    config = load(tmp_path, a_toml(), env)

    # Assert
    assert config.library.token is None


def test_a_token_of_exactly_24_characters_is_accepted(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_token("a" * 24))

    # Assert
    assert config.library.token == "a" * 24


def test_a_token_shorter_than_24_characters_is_refused_naming_the_variable_and_the_rule(
    tmp_path: Path,
) -> None:
    # Execute
    refusal = load_message(tmp_path, a_toml(), with_token("a" * 23))

    # Assert
    assert f"{TOKEN_VAR} must be at least 24 characters" in refusal


@pytest.mark.parametrize("unsafe", [" ", ";", "é"])
def test_a_token_with_a_character_unsafe_in_a_url_or_cookie_is_refused(
    tmp_path: Path, unsafe: str
) -> None:
    # Execute
    refusal = load_message(tmp_path, a_toml(), with_token("a" * 12 + unsafe + "a" * 12))

    # Assert
    assert f"{TOKEN_VAR} may only use A-Z a-z 0-9 - . _ ~" in refusal


@pytest.mark.parametrize("bad", ["short", "a" * 12 + " " + "a" * 12])
def test_a_refused_token_never_appears_in_the_message(tmp_path: Path, bad: str) -> None:
    # Execute
    refusal = load_message(tmp_path, a_toml(), with_token(bad))

    # Assert
    assert bad not in refusal


def test_a_token_in_the_config_file_is_refused(tmp_path: Path) -> None:
    # Execute
    refusal = load_message(tmp_path, with_library(f'token = "{TOKEN}"'))

    # Assert
    assert "library.token is not allowed: put secrets in env, not in the config file" in refusal


def test_the_token_never_appears_in_the_repr_of_the_config(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_token(TOKEN))

    # Assert
    assert TOKEN not in repr(config)


def test_the_example_files_library_block_works_once_uncommented(tmp_path: Path) -> None:
    # Setup
    lines = EXAMPLE_FILE.read_text(encoding="utf-8").splitlines()
    first = lines.index(LIBRARY_BLOCK_LINES[0])
    block = slice(first, first + len(LIBRARY_BLOCK_LINES))
    lines[block] = [line.removeprefix("# ") for line in lines[block]]

    # Execute
    config = load(tmp_path, "\n".join(lines), with_key())

    # Assert
    assert config.library == LibraryConfig(bind="0.0.0.0", port=8765, token=None)
