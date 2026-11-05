from pathlib import Path

from config_toml import (
    OLLAMA_TABLE,
    OPENROUTER_TABLE,
    TASKS_TO_OPENROUTER,
    a_toml,
    load_message,
    with_key,
)


def test_provider_without_its_table_names_the_missing_table(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(provider="openrouter", tables=OLLAMA_TABLE), with_key())

    # Assert
    assert "llm.openrouter" in message


def test_ollama_provider_without_its_table_names_the_missing_table(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(tables=OPENROUTER_TABLE), with_key())

    # Assert
    assert "llm.ollama" in message


def test_openrouter_busy_fallback_without_the_table_names_the_missing_table(
    tmp_path: Path,
) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(llm_keys='busy_fallback = "openrouter"'), with_key())

    # Assert
    assert "llm.openrouter" in message


def test_task_override_without_the_table_names_the_missing_table(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(tables=OLLAMA_TABLE + TASKS_TO_OPENROUTER), with_key())

    # Assert
    assert "llm.openrouter" in message


def test_provider_is_required(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, "[llm]\n" + OLLAMA_TABLE)

    # Assert
    assert "llm.provider" in message


def test_unknown_provider_name_names_the_key_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(provider="gpt"))

    # Assert
    assert "llm.provider" in message


def test_unknown_busy_fallback_names_the_key_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(llm_keys='busy_fallback = "never"'))

    # Assert
    assert "llm.busy_fallback" in message


def test_unknown_task_provider_names_the_key_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path, a_toml(tables=OLLAMA_TABLE + '[llm.tasks]\nsuggestions = "gpt"\n')
    )

    # Assert
    assert "llm.tasks.suggestions" in message


def test_unknown_task_name_names_the_key_path(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path, a_toml(tables=OLLAMA_TABLE + '[llm.tasks]\nsummaries = "ollama"\n')
    )

    # Assert
    assert "llm.tasks.summaries" in message


def test_provider_table_requires_a_model(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(tables="[llm.ollama]\n"))

    # Assert
    assert "llm.ollama.model" in message


def test_a_configured_base_url_with_credentials_is_rejected_naming_the_key(tmp_path: Path) -> None:
    # Setup
    tables = '[llm.ollama]\nmodel = "m"\nbase_url = "http://user:hunter2@gpu:1/v1"\n'

    # Execute
    message = load_message(tmp_path, a_toml(tables=tables))

    # Assert
    assert "llm.ollama.base_url" in message


def test_a_configured_base_url_never_echoes_its_credentials_in_the_error(tmp_path: Path) -> None:
    # Setup
    tables = '[llm.ollama]\nmodel = "m"\nbase_url = "http://user:hunter2@gpu:1/v1"\n'

    # Execute
    message = load_message(tmp_path, a_toml(tables=tables))

    # Assert
    assert "hunter2" not in message


def test_a_plain_http_openrouter_base_url_is_rejected_naming_the_key(tmp_path: Path) -> None:
    # Setup
    tables = '[llm.openrouter]\nmodel = "x"\nbase_url = "http://openrouter.ai/api/v1"\n'

    # Execute
    message = load_message(tmp_path, a_toml(provider="openrouter", tables=tables), with_key())

    # Assert
    assert "llm.openrouter.base_url" in message


def test_blank_vision_model_in_the_file_is_a_config_error_naming_the_key(tmp_path: Path) -> None:
    # Setup
    tables = '[llm.ollama]\nmodel = "m"\nvision_model = ""\n'

    # Execute
    message = load_message(tmp_path, a_toml(tables=tables))

    # Assert
    assert "llm.ollama.vision_model" in message
