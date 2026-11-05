import json

import httpx
from builders import an_ollama_settings, an_openrouter_settings
from config_builders import an_llm_config
from fakes.fake_providers import FakeProviders

from stash.app.providers import chat_models, eval_targets, model_unloader, own_vram_usage
from stash.config import LlmConfig, LlmTask, ModelChoice, ProviderName, Thinking
from stash.llm import ChatMessage, ChatModel

SCHEMA = {"type": "object"}
BOTH = an_llm_config(
    providers={
        ProviderName.OLLAMA: an_ollama_settings(vision_model="llava"),
        ProviderName.OPENROUTER: an_openrouter_settings(),
    }
)
OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
THINKING_FIELDS = {"reasoning_effort", "reasoning"}
FILING_OFF = an_llm_config(providers=BOTH.providers, thinking={LlmTask.FILING: Thinking.OFF})
VISION_OFF = an_llm_config(providers=BOTH.providers, thinking={LlmTask.VISION: Thinking.OFF})
OPENROUTER_ONLY = an_llm_config(
    provider=ProviderName.OPENROUTER, providers={ProviderName.OPENROUTER: an_openrouter_settings()}
)


def first_request_json(providers: FakeProviders) -> dict[str, object]:
    body: dict[str, object] = json.loads(providers.requests[0].content)
    return body


def vision_model_of(llm: LlmConfig, client: httpx.Client) -> ChatModel:
    vision_model = eval_targets(llm, client, chat_models(llm, client))[OLLAMA].vision_model
    assert vision_model is not None
    return vision_model


def ask(model: ChatModel) -> None:
    model.complete_json([ChatMessage.text("user", "hello")], SCHEMA, "probe")


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


def test_each_eval_target_is_labelled_with_its_provider_and_model() -> None:
    # Setup
    client = FakeProviders().client()

    # Execute
    targets = eval_targets(BOTH, client, chat_models(BOTH, client))

    # Assert
    assert {name: target.label for name, target in targets.items()} == {
        ProviderName.OLLAMA: "ollama:llama3:8b",
        ProviderName.OPENROUTER: "openrouter:cloud/model",
    }


def test_an_eval_target_uses_the_providers_own_chat_model() -> None:
    # Setup
    client = FakeProviders().client()
    models = chat_models(BOTH, client)

    # Execute
    targets = eval_targets(BOTH, client, models)

    # Assert
    assert (
        targets[ProviderName.OLLAMA].model
        is models[ModelChoice(ProviderName.OLLAMA, Thinking.DEFAULT)]
    )


def test_an_eval_target_sends_images_to_the_configured_vision_model() -> None:
    # Setup
    providers = FakeProviders()
    client = providers.client()
    vision_model = vision_model_of(BOTH, client)

    # Execute
    ask(vision_model)

    # Assert
    assert json.loads(providers.requests[0].content)["model"] == "llava"


def test_an_eval_target_without_a_vision_model_has_none() -> None:
    # Setup
    client = FakeProviders().client()

    # Execute
    targets = eval_targets(BOTH, client, chat_models(BOTH, client))

    # Assert
    assert targets[ProviderName.OPENROUTER].vision_model is None


def test_only_configured_providers_get_an_eval_target() -> None:
    # Setup
    client = FakeProviders().client()

    # Execute
    targets = eval_targets(OPENROUTER_ONLY, client, chat_models(OPENROUTER_ONLY, client))

    # Assert
    assert set(targets) == {ProviderName.OPENROUTER}


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
    assert THINKING_FIELDS & set(first_request_json(providers)) == set()


def test_an_eval_targets_text_model_follows_the_filing_thinking_setting() -> None:
    # Setup
    client = FakeProviders().client()
    models = chat_models(FILING_OFF, client)

    # Execute
    targets = eval_targets(FILING_OFF, client, models)

    # Assert
    assert targets[OLLAMA].model is models[ModelChoice(OLLAMA, Thinking.OFF)]


def test_an_eval_targets_vision_model_follows_the_vision_thinking_setting() -> None:
    # Setup
    providers = FakeProviders()
    client = providers.client()
    vision_model = vision_model_of(VISION_OFF, client)

    # Execute
    ask(vision_model)

    # Assert
    assert first_request_json(providers)["reasoning_effort"] == "none"


def test_an_eval_targets_vision_model_does_not_inherit_the_filing_thinking_setting() -> None:
    # Setup
    providers = FakeProviders()
    client = providers.client()
    vision_model = vision_model_of(FILING_OFF, client)

    # Execute
    ask(vision_model)

    # Assert
    assert THINKING_FIELDS & set(first_request_json(providers)) == set()
