import json

from fakes.fake_providers import FakeProviders
from provider_rig import (
    BOTH,
    FILING_OFF,
    OLLAMA,
    OPENROUTER,
    OPENROUTER_ONLY,
    ask,
    first_request_json,
    thinking_fields_of,
)

from stash.app.providers import chat_models, model_unloader, own_vram_usage
from stash.config import LlmConfig, ModelChoice, ProviderName, Thinking
from stash.llm import ChatModel


def models_in(providers: FakeProviders, llm: LlmConfig) -> dict[ModelChoice, ChatModel]:
    return chat_models(llm, providers.client())


def test_there_is_a_chat_model_for_each_configured_provider() -> None:
    # Execute
    models = models_in(FakeProviders(), BOTH)

    # Assert
    assert set(models) == {
        ModelChoice(ProviderName.OLLAMA, Thinking.DEFAULT),
        ModelChoice(ProviderName.OPENROUTER, Thinking.DEFAULT),
    }


def test_each_chat_model_talks_to_its_own_providers_endpoint() -> None:
    # Setup
    providers = FakeProviders()
    models = models_in(providers, BOTH)

    # Execute
    ask(models[ModelChoice(ProviderName.OPENROUTER, Thinking.DEFAULT)])
    ask(models[ModelChoice(ProviderName.OLLAMA, Thinking.DEFAULT)])

    # Assert
    assert [str(request.url) for request in providers.requests] == [
        "https://openrouter.ai/api/v1/chat/completions",
        "http://localhost:11434/v1/chat/completions",
    ]


def test_with_ollama_configured_its_loaded_models_count_as_stashs_own_vram() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    own_vram_usage(BOTH, providers.client()).own_mib()

    # Assert
    assert [request.url.path for request in providers.requests] == ["/api/ps"]


def test_without_ollama_no_vram_counts_as_stashs_own_and_nothing_is_asked() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    own = own_vram_usage(OPENROUTER_ONLY, providers.client()).own_mib()

    # Assert
    assert (own, providers.requests) == (0, [])


def test_with_ollama_configured_unloading_posts_keep_alive_zero_for_its_model() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    model_unloader(BOTH, providers.client()).unload()

    # Assert
    assert [json.loads(request.content) for request in providers.requests] == [
        {"model": "llama3:8b", "keep_alive": 0}
    ]


def test_without_ollama_there_is_no_model_to_unload_and_nothing_is_sent() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    model_unloader(OPENROUTER_ONLY, providers.client()).unload()

    # Assert
    assert providers.requests == []


def test_chat_models_are_built_for_exactly_the_choices_the_config_needs() -> None:
    # Execute
    models = models_in(FakeProviders(), FILING_OFF)

    # Assert
    assert set(models) == FILING_OFF.model_choices()


def test_the_openrouter_off_model_sends_openrouters_thinking_field() -> None:
    # Setup
    providers = FakeProviders()
    models = models_in(providers, FILING_OFF)

    # Execute
    ask(models[ModelChoice(OPENROUTER, Thinking.OFF)])

    # Assert
    assert first_request_json(providers)["reasoning"] == {"effort": "none"}


def test_the_ollama_off_model_sends_ollamas_thinking_field() -> None:
    # Setup
    providers = FakeProviders()
    models = models_in(providers, FILING_OFF)

    # Execute
    ask(models[ModelChoice(OLLAMA, Thinking.OFF)])

    # Assert
    assert first_request_json(providers)["reasoning_effort"] == "none"


def test_a_default_model_sends_no_thinking_field_even_when_another_task_is_off() -> None:
    # Setup
    providers = FakeProviders()
    models = models_in(providers, FILING_OFF)

    # Execute
    ask(models[ModelChoice(OLLAMA, Thinking.DEFAULT)])

    # Assert
    assert thinking_fields_of(providers) == {}
