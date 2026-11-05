import json

import pytest
from builders import an_ollama_settings, an_openrouter_settings
from config_builders import an_llm_config
from eval_builders import target_for
from fakes.chat_model import FakeChatModel
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

from stash.app.providers import eval_chat_models, eval_targets, vision_models
from stash.config import LlmConfig, LlmTask, ModelChoice, ProviderName, Thinking
from stash.evaluation import EvalTargets
from stash.llm import ChatModel

OFF_FIELDS: dict[ProviderName, dict[str, object]] = {
    OLLAMA: {"reasoning_effort": "none"},
    OPENROUTER: {"reasoning": {"effort": "none"}},
}
VISION_OFF = an_llm_config(providers=BOTH.providers, thinking={LlmTask.VISION: Thinking.OFF})
NO_VISION = an_llm_config(
    providers={
        OLLAMA: an_ollama_settings(),
        OPENROUTER: an_openrouter_settings(),
    }
)


def targets_in(providers: FakeProviders, llm: LlmConfig) -> EvalTargets:
    client = providers.client()
    return eval_targets(llm, eval_chat_models(llm, client), vision_models(llm, client))


def vision_model_of(llm: LlmConfig, providers: FakeProviders, thinking: Thinking) -> ChatModel:
    return target_for(targets_in(providers, llm), OLLAMA, thinking).image_model


def test_each_eval_target_is_labelled_with_its_provider_and_model() -> None:
    # Execute
    targets = targets_in(FakeProviders(), BOTH)

    # Assert
    assert {target.label for target in targets.targets} == {
        "ollama:llama3:8b vision=llava thinking=default",
        "ollama:llama3:8b vision=llava thinking=off",
        "openrouter:cloud/model thinking=default",
        "openrouter:cloud/model thinking=off",
    }


def test_an_eval_target_uses_the_model_given_for_its_choice() -> None:
    # Setup
    models = {
        ModelChoice(provider, thinking): FakeChatModel()
        for provider in ProviderName
        for thinking in Thinking
    }

    # Execute
    targets = eval_targets(NO_VISION, models, {})

    # Assert
    assert (
        target_for(targets, OPENROUTER, Thinking.OFF).model
        is models[ModelChoice(OPENROUTER, Thinking.OFF)]
    )


def test_an_eval_target_uses_the_vision_model_given_for_its_choice() -> None:
    # Setup
    choice = ModelChoice(OLLAMA, Thinking.OFF)
    vision = FakeChatModel()
    other = ModelChoice(OLLAMA, Thinking.DEFAULT)
    models = {choice: FakeChatModel(), other: FakeChatModel()}

    # Execute
    targets = eval_targets(BOTH, models, {choice: vision, other: FakeChatModel()})

    # Assert
    assert target_for(targets, OLLAMA, Thinking.OFF).image_model is vision


def test_an_eval_target_without_a_given_vision_model_has_none() -> None:
    # Setup
    models = {ModelChoice(OLLAMA, thinking): FakeChatModel() for thinking in Thinking}

    # Execute
    targets = eval_targets(NO_VISION, models, {})

    # Assert
    assert target_for(targets, OLLAMA, Thinking.DEFAULT).vision is None


def test_an_eval_target_sends_images_to_the_configured_vision_model() -> None:
    # Setup
    providers = FakeProviders()
    vision_model = vision_model_of(BOTH, providers, Thinking.DEFAULT)

    # Execute
    ask(vision_model)

    # Assert
    assert json.loads(providers.requests[0].content)["model"] == "llava"


def test_an_eval_target_without_a_vision_model_has_none() -> None:
    # Execute
    targets = targets_in(FakeProviders(), BOTH)

    # Assert
    assert target_for(targets, OPENROUTER, Thinking.DEFAULT).vision is None


def test_only_configured_providers_get_an_eval_target() -> None:
    # Execute
    targets = targets_in(FakeProviders(), OPENROUTER_ONLY)

    # Assert
    assert {target.choice.provider for target in targets.targets} == {OPENROUTER}


def test_every_configured_provider_gets_an_eval_chat_model_for_each_thinking_value() -> None:
    # Execute
    models = eval_chat_models(BOTH, FakeProviders().client())

    # Assert
    assert set(models) == {
        ModelChoice(provider, thinking) for provider in ProviderName for thinking in Thinking
    }


def test_eval_chat_models_cover_both_thinking_values_whatever_the_config_asks_for() -> None:
    # Execute
    models = eval_chat_models(FILING_OFF, FakeProviders().client())

    # Assert
    assert {choice.thinking for choice in models} == set(Thinking)


def test_only_providers_with_a_vision_model_get_vision_models_for_each_thinking_value() -> None:
    # Execute
    models = vision_models(BOTH, FakeProviders().client())

    # Assert
    assert set(models) == {ModelChoice(OLLAMA, thinking) for thinking in Thinking}


def test_no_vision_models_are_built_when_no_provider_has_one() -> None:
    # Execute
    models = vision_models(NO_VISION, FakeProviders().client())

    # Assert
    assert models == {}


def test_the_eval_targets_default_thinking_is_the_configured_filing_thinking() -> None:
    # Execute
    targets = targets_in(FakeProviders(), FILING_OFF)

    # Assert
    assert targets.configured is Thinking.OFF


def test_the_eval_targets_default_thinking_is_default_when_nothing_is_configured() -> None:
    # Execute
    targets = targets_in(FakeProviders(), BOTH)

    # Assert
    assert targets.configured is Thinking.DEFAULT


def test_the_eval_targets_default_thinking_ignores_the_vision_thinking_setting() -> None:
    # Execute
    targets = targets_in(FakeProviders(), VISION_OFF)

    # Assert
    assert targets.configured is Thinking.DEFAULT


@pytest.mark.parametrize("provider", list(ProviderName))
def test_an_eval_targets_text_model_sends_the_off_field_when_the_target_is_off(
    provider: ProviderName,
) -> None:
    # Setup
    providers = FakeProviders()
    target = target_for(targets_in(providers, BOTH), provider, Thinking.OFF)

    # Execute
    ask(target.model)

    # Assert
    assert thinking_fields_of(providers) == OFF_FIELDS[provider]


@pytest.mark.parametrize("provider", list(ProviderName))
def test_an_eval_targets_text_model_sends_no_thinking_field_when_the_target_is_default(
    provider: ProviderName,
) -> None:
    # Setup
    providers = FakeProviders()
    target = target_for(targets_in(providers, FILING_OFF), provider, Thinking.DEFAULT)

    # Execute
    ask(target.model)

    # Assert
    assert thinking_fields_of(providers) == {}


def test_an_off_eval_targets_vision_model_sends_the_off_field() -> None:
    # Setup
    providers = FakeProviders()
    vision_model = vision_model_of(BOTH, providers, Thinking.OFF)

    # Execute
    ask(vision_model)

    # Assert
    assert thinking_fields_of(providers) == OFF_FIELDS[OLLAMA]


def test_an_off_eval_targets_vision_model_still_asks_the_vision_model() -> None:
    # Setup
    providers = FakeProviders()
    vision_model = vision_model_of(BOTH, providers, Thinking.OFF)

    # Execute
    ask(vision_model)

    # Assert
    assert first_request_json(providers)["model"] == "llava"


def test_a_default_eval_targets_vision_model_ignores_the_vision_off_setting() -> None:
    # Setup
    providers = FakeProviders()
    vision_model = vision_model_of(VISION_OFF, providers, Thinking.DEFAULT)

    # Execute
    ask(vision_model)

    # Assert
    assert thinking_fields_of(providers) == {}


def test_an_eval_targets_text_model_follows_the_filing_thinking_setting() -> None:
    # Setup
    providers = FakeProviders()
    targets = targets_in(providers, FILING_OFF)

    # Execute
    ask(targets.select(None, None)[0].model)

    # Assert
    assert thinking_fields_of(providers) == OFF_FIELDS[OLLAMA]


def test_a_vision_model_the_vision_mapping_lacks_raises_key_error() -> None:
    # Setup
    models = {ModelChoice(OLLAMA, thinking): FakeChatModel() for thinking in Thinking}

    # Execute / Assert
    with pytest.raises(KeyError):
        eval_targets(BOTH, models, {})
