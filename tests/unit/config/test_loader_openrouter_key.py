from pathlib import Path

from config_toml import (
    KEY,
    OLLAMA_TABLE,
    OPENROUTER_TABLE,
    TASKS_TO_OPENROUTER,
    a_toml,
    load,
    load_message,
    with_key,
    without_key,
)

from stash.config import LlmTask, ProviderName


def test_ollama_settings_never_carry_an_api_key(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_key())

    # Assert
    assert config.llm.providers[ProviderName.OLLAMA].api_key is None


def test_openrouter_table_defaults_its_base_url(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE), with_key())

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].base_url == "https://openrouter.ai/api/v1"


def test_openrouter_table_carries_the_key_from_the_environment(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE), with_key())

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].api_key == KEY


def test_unused_openrouter_table_without_key_loads_with_no_api_key(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE), without_key())

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].api_key is None


def test_unused_openrouter_table_with_blank_key_loads_with_no_api_key(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE),
        with_key(OPENROUTER_API_KEY="  "),
    )

    # Assert
    assert config.llm.providers[ProviderName.OPENROUTER].api_key is None


def test_ollama_provider_with_key_present_and_no_openrouter_table_loads(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(), with_key())

    # Assert
    assert config.llm.provider is ProviderName.OLLAMA


def test_openrouter_provider_with_key_present_loads(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(provider="openrouter", tables=OPENROUTER_TABLE), with_key())

    # Assert
    assert config.llm.provider is ProviderName.OPENROUTER


def test_openrouter_provider_without_key_names_the_variable(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(provider="openrouter", tables=OPENROUTER_TABLE))

    # Assert
    assert "OPENROUTER_API_KEY" in message


def test_openrouter_provider_with_blank_key_names_the_variable(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path,
        a_toml(provider="openrouter", tables=OPENROUTER_TABLE),
        with_key(OPENROUTER_API_KEY=""),
    )

    # Assert
    assert "OPENROUTER_API_KEY" in message


def test_openrouter_busy_fallback_with_key_present_loads(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        a_toml(llm_keys='busy_fallback = "openrouter"', tables=OLLAMA_TABLE + OPENROUTER_TABLE),
        with_key(),
    )

    # Assert
    assert config.llm.busy_fallback == "openrouter"


def test_openrouter_busy_fallback_without_key_names_the_variable(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path,
        a_toml(llm_keys='busy_fallback = "openrouter"', tables=OLLAMA_TABLE + OPENROUTER_TABLE),
    )

    # Assert
    assert "OPENROUTER_API_KEY" in message


def test_wait_busy_fallback_without_key_loads(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        a_toml(llm_keys='busy_fallback = "wait"', tables=OLLAMA_TABLE + OPENROUTER_TABLE),
    )

    # Assert
    assert config.llm.busy_fallback == "wait"


def test_task_override_to_openrouter_sends_that_task_to_openrouter(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE + TASKS_TO_OPENROUTER),
        with_key(),
    )

    # Assert
    assert config.llm.provider_for(LlmTask.SUGGESTIONS) is ProviderName.OPENROUTER


def test_task_override_leaves_other_tasks_on_the_default_provider(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE + TASKS_TO_OPENROUTER),
        with_key(),
    )

    # Assert
    assert config.llm.provider_for(LlmTask.FILING) is ProviderName.OLLAMA


def test_task_override_to_openrouter_without_key_names_the_variable(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path, a_toml(tables=OLLAMA_TABLE + OPENROUTER_TABLE + TASKS_TO_OPENROUTER)
    )

    # Assert
    assert "OPENROUTER_API_KEY" in message
