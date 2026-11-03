from pathlib import Path

import pytest
from config_toml import KEY, a_toml, load, load_message, with_key, without_key

import stash.config
from stash.config import ConfigError, ProviderName
from stash.config.loader import DEFAULT_BASE_URLS, load_config

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "deploy" / "stash.toml.example"


def test_missing_file_names_the_path(tmp_path: Path) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"nope\.toml"):
        load_config(tmp_path / "nope.toml", without_key())


def test_invalid_toml_names_the_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, "[llm\nprovider = ")

    # Assert
    assert "stash.toml" in message


def test_loaded_config_mappings_are_read_only(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    with pytest.raises(TypeError):
        config.llm.providers[ProviderName.OPENROUTER] = config.llm.providers[ProviderName.OLLAMA]


def test_example_file_loads_with_home_and_openrouter_key() -> None:
    # Execute
    config = load_config(EXAMPLE_FILE, with_key())

    # Assert
    assert config.llm.provider is ProviderName.OLLAMA


def test_example_file_carries_the_environment_key_in_the_unused_openrouter_table() -> None:
    # Execute
    config = load_config(EXAMPLE_FILE, with_key())

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].api_key == KEY


def test_example_file_loads_without_the_openrouter_key() -> None:
    # Execute
    config = load_config(EXAMPLE_FILE, without_key())

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].api_key is None


def test_the_default_base_urls_cannot_be_modified() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        DEFAULT_BASE_URLS[ProviderName.OLLAMA] = "http://elsewhere/v1"


def test_the_config_package_does_not_re_export_the_loader() -> None:
    # Assert
    assert not hasattr(stash.config, "load_config")
