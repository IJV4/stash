from pathlib import Path

import pytest
from config_toml import (
    KEY,
    OLLAMA_TABLE,
    OPENROUTER_TABLE,
    a_toml,
    load,
    load_message,
    with_key,
)


def test_api_key_in_the_ollama_table_says_to_put_secrets_in_env(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(tables=OLLAMA_TABLE + 'api_key = "sk-in-file"\n'))

    # Assert
    assert "put secrets in env" in message


def test_api_key_in_the_openrouter_table_says_to_put_secrets_in_env(tmp_path: Path) -> None:
    # Setup
    tables = OLLAMA_TABLE + OPENROUTER_TABLE + 'api_key = "sk-in-file"\n'

    # Execute
    message = load_message(tmp_path, a_toml(tables=tables), with_key())

    # Assert
    assert "put secrets in env" in message


def test_api_key_in_the_file_is_never_echoed_in_the_error(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(tables=OLLAMA_TABLE + 'api_key = "sk-in-file"\n'))

    # Assert
    assert "sk-in-file" not in message


def test_environment_key_is_never_echoed_in_an_error(tmp_path: Path) -> None:
    # Setup
    tables = OLLAMA_TABLE + OPENROUTER_TABLE + "typo = 1\n"

    # Execute
    message = load_message(tmp_path, a_toml(tables=tables), with_key())

    # Assert
    assert KEY not in message


def test_environment_key_never_appears_in_the_config_repr(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE), with_key())

    # Assert
    assert KEY not in repr(config)


@pytest.mark.parametrize(
    ("text", "path"),
    [
        (a_toml(top="datadir = 1"), "datadir"),
        (a_toml(llm_keys="busy_fallbak = 1"), "llm.busy_fallbak"),
        (a_toml(tables=OLLAMA_TABLE + "modle = 1\n"), "llm.ollama.modle"),
        (a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE + "modle = 1\n"), "llm.openrouter.modle"),
        (a_toml(tables=OLLAMA_TABLE + "[llm.olama]\nmodel = 'm'\n"), "llm.olama"),
        (a_toml(tables=OLLAMA_TABLE + "[gpu]\nmin_free = 1\n"), "gpu.min_free"),
        (a_toml(tables=OLLAMA_TABLE + "[extra]\nx = 1\n"), "extra"),
    ],
)
def test_unknown_key_names_its_full_path(tmp_path: Path, text: str, path: str) -> None:
    # Execute
    message = load_message(tmp_path, text, with_key())

    # Assert
    assert path in message


@pytest.mark.parametrize(
    ("text", "path"),
    [
        (a_toml(top="data_dir = 5"), "data_dir"),
        (a_toml(top='burst_window_seconds = "soon"'), "burst_window_seconds"),
        (a_toml(top="burst_window_seconds = true"), "burst_window_seconds"),
        (a_toml(top="timezone = 3"), "timezone"),
        (a_toml(llm_keys="busy_fallback = 3"), "llm.busy_fallback"),
        (a_toml(tables="[llm.ollama]\nmodel = 3\n"), "llm.ollama.model"),
        (
            a_toml(tables=OLLAMA_TABLE + '[gpu]\nmin_free_vram_mib = "lots"\n'),
            "gpu.min_free_vram_mib",
        ),
        (
            a_toml(tables=OLLAMA_TABLE + "[gpu]\nmin_free_vram_mib = 9000.5\n"),
            "gpu.min_free_vram_mib",
        ),
        (
            a_toml(tables=OLLAMA_TABLE + "[gpu]\nmin_free_vram_mib = true\n"),
            "gpu.min_free_vram_mib",
        ),
        (a_toml(tables=OLLAMA_TABLE + "[gpu]\nmanual_off_hours = true\n"), "gpu.manual_off_hours"),
        ("llm = 3\n", "llm"),
    ],
)
def test_value_of_the_wrong_type_names_its_key_path(tmp_path: Path, text: str, path: str) -> None:
    # Execute
    message = load_message(tmp_path, text)

    # Assert
    assert path in message
