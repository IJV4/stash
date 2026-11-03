from typing import get_args

import pytest
from builders import API_KEY, an_ollama_settings, an_openrouter_settings
from config_builders import an_llm_config

from stash.config import BusyFallback, ConfigError, LlmTask, ProviderName
from stash.config.model import BUSY_FALLBACKS


def test_provider_names_are_the_config_vocabulary() -> None:
    # Assert
    assert [name.value for name in ProviderName] == ["ollama", "openrouter"]


def test_llm_tasks_are_the_config_vocabulary() -> None:
    # Assert
    assert [task.value for task in LlmTask] == ["filing", "suggestions", "vision"]


def test_the_busy_fallbacks_are_exactly_the_values_of_the_busy_fallback_type() -> None:
    # Assert
    assert get_args(BusyFallback) == BUSY_FALLBACKS


def test_llm_config_with_provider_missing_from_providers_raises_naming_its_table() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.openrouter"):
        an_llm_config(provider=ProviderName.OPENROUTER)


def test_llm_config_with_task_provider_missing_from_providers_raises_naming_its_table() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.openrouter"):
        an_llm_config(tasks={LlmTask.SUGGESTIONS: ProviderName.OPENROUTER})


def test_llm_config_with_openrouter_fallback_but_no_openrouter_table_raises() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.openrouter"):
        an_llm_config(busy_fallback="openrouter")


def test_llm_config_using_openrouter_without_api_key_names_the_variable() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        an_llm_config(
            provider=ProviderName.OPENROUTER,
            providers={ProviderName.OPENROUTER: an_openrouter_settings(api_key=None)},
        )


def test_llm_config_with_unused_openrouter_settings_needs_no_api_key() -> None:
    # Setup
    providers = {
        ProviderName.OLLAMA: an_ollama_settings(),
        ProviderName.OPENROUTER: an_openrouter_settings(api_key=None),
    }

    # Execute
    config = an_llm_config(providers=providers)

    # Assert
    assert config.providers[ProviderName.OPENROUTER].api_key is None


def test_llm_config_with_unknown_busy_fallback_raises_config_error() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="busy_fallback"):
        an_llm_config(busy_fallback="never")


def test_llm_config_error_never_contains_the_api_key() -> None:
    # Execute
    with pytest.raises(ConfigError) as error:
        an_llm_config(provider=ProviderName.OPENROUTER)

    # Assert
    assert API_KEY not in str(error.value)


def test_provider_for_a_task_without_override_is_the_default_provider() -> None:
    # Setup
    config = an_llm_config()

    # Assert
    assert config.provider_for(LlmTask.FILING) is ProviderName.OLLAMA


def test_provider_for_a_task_with_override_is_the_override() -> None:
    # Setup
    config = an_llm_config(
        providers={
            ProviderName.OLLAMA: an_ollama_settings(),
            ProviderName.OPENROUTER: an_openrouter_settings(),
        },
        tasks={LlmTask.SUGGESTIONS: ProviderName.OPENROUTER},
    )

    # Assert
    assert config.provider_for(LlmTask.SUGGESTIONS) is ProviderName.OPENROUTER


def test_llm_config_providers_cannot_be_mutated_afterwards() -> None:
    # Setup
    config = an_llm_config()

    # Execute / Assert
    with pytest.raises(TypeError):
        config.providers[ProviderName.OPENROUTER] = an_openrouter_settings()


def test_llm_config_tasks_cannot_be_mutated_afterwards() -> None:
    # Setup
    config = an_llm_config()

    # Execute / Assert
    with pytest.raises(TypeError):
        config.tasks[LlmTask.FILING] = ProviderName.OLLAMA


def test_llm_config_is_isolated_from_the_dict_it_was_built_from() -> None:
    # Setup
    tasks: dict[LlmTask, ProviderName] = {}
    config = an_llm_config(tasks=tasks)

    # Execute
    tasks[LlmTask.FILING] = ProviderName.OPENROUTER

    # Assert
    assert dict(config.tasks) == {}
