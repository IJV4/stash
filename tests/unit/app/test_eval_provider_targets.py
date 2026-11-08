import pytest
from fakes.chat_model import FakeChatModel
from fakes.fake_providers import FakeProviders
from provider_rig import (
    BOTH,
    FILING_OFF,
    OLLAMA,
    OPENROUTER,
    ask,
    thinking_fields_of,
)

from stash.app.providers import eval_chat_models, eval_targets, vision_models
from stash.config import LlmConfig, ModelChoice, ProviderName, Thinking
from stash.evaluation import EvalTargets

OFF_FIELDS: dict[ProviderName, dict[str, object]] = {
    OLLAMA: {"reasoning_effort": "none"},
    OPENROUTER: {"reasoning": {"effort": "none"}},
}


def targets_in(providers: FakeProviders, llm: LlmConfig) -> EvalTargets:
    client = providers.client()
    return eval_targets(llm, eval_chat_models(llm, client), vision_models(llm, client))


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
