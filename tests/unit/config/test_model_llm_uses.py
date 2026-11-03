from builders import an_ollama_settings, an_openrouter_settings
from config_builders import an_llm_config

from stash.config import LlmConfig, LlmTask, ProviderName

BOTH = {
    ProviderName.OLLAMA: an_ollama_settings(),
    ProviderName.OPENROUTER: an_openrouter_settings(),
}
ONLY_OPENROUTER = {ProviderName.OPENROUTER: an_openrouter_settings()}


def ollama_only() -> LlmConfig:
    return an_llm_config()


def test_the_default_provider_is_used() -> None:
    # Execute
    used = ollama_only().uses(ProviderName.OLLAMA)

    # Assert
    assert used is True


def test_a_provider_that_is_configured_but_chosen_nowhere_is_not_used() -> None:
    # Setup
    config = an_llm_config(providers=BOTH)

    # Execute
    used = config.uses(ProviderName.OPENROUTER)

    # Assert
    assert used is False


def test_openrouter_chosen_as_the_default_provider_is_used() -> None:
    # Setup
    config = an_llm_config(provider=ProviderName.OPENROUTER, providers=ONLY_OPENROUTER)

    # Execute
    used = config.uses(ProviderName.OPENROUTER)

    # Assert
    assert used is True


def test_ollama_is_not_used_when_openrouter_is_the_only_choice() -> None:
    # Setup
    config = an_llm_config(provider=ProviderName.OPENROUTER, providers=ONLY_OPENROUTER)

    # Execute
    used = config.uses(ProviderName.OLLAMA)

    # Assert
    assert used is False


def test_a_provider_chosen_for_one_task_is_used() -> None:
    # Setup
    config = an_llm_config(providers=BOTH, tasks={LlmTask.SUGGESTIONS: ProviderName.OPENROUTER})

    # Execute
    used = config.uses(ProviderName.OPENROUTER)

    # Assert
    assert used is True


def test_the_default_provider_stays_used_when_only_one_task_is_moved_away() -> None:
    # Setup
    config = an_llm_config(providers=BOTH, tasks={LlmTask.SUGGESTIONS: ProviderName.OPENROUTER})

    # Execute
    used = config.uses(ProviderName.OLLAMA)

    # Assert
    assert used is True


def test_openrouter_as_the_busy_fallback_is_used() -> None:
    # Setup
    config = an_llm_config(providers=BOTH, busy_fallback="openrouter")

    # Execute
    used = config.uses(ProviderName.OPENROUTER)

    # Assert
    assert used is True


def test_waiting_as_the_busy_fallback_uses_no_extra_provider() -> None:
    # Setup
    config = an_llm_config(providers=BOTH, busy_fallback="wait")

    # Execute
    used = config.uses(ProviderName.OPENROUTER)

    # Assert
    assert used is False


def test_ollama_is_not_used_when_openrouter_is_both_the_default_and_the_busy_fallback() -> None:
    # Setup
    config = an_llm_config(
        provider=ProviderName.OPENROUTER, providers=ONLY_OPENROUTER, busy_fallback="openrouter"
    )

    # Execute
    used = config.uses(ProviderName.OLLAMA)

    # Assert
    assert used is False
