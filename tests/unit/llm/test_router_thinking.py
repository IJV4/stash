import pytest
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from router_builders import a_router_config

from stash.config import (
    LlmConfig,
    LlmTask,
    ModelChoice,
    ProviderName,
    Thinking,
)
from stash.llm import ChatMessage, ChatModel, ModelRouter

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
DEFAULT = Thinking.DEFAULT
OFF = Thinking.OFF
SCHEMA: dict[str, object] = {"type": "object"}
HELLO = [ChatMessage.text("user", "hello")]
FILING_OFF = {LlmTask.FILING: OFF}


def models_for(config: LlmConfig) -> dict[ModelChoice, FakeChatModel]:
    return {choice: FakeChatModel() for choice in config.model_choices()}


def router_over(
    config: LlmConfig, models: dict[ModelChoice, FakeChatModel], busy: bool = False
) -> ModelRouter:
    chat_models: dict[ModelChoice, ChatModel] = dict(models)
    return ModelRouter(config, chat_models, FakeBusy(busy))


def test_a_router_without_a_model_for_a_choice_the_config_uses_names_it() -> None:
    # Setup
    config = a_router_config(thinking=FILING_OFF)
    models = models_for(config)
    del models[ModelChoice(OLLAMA, OFF)]

    # Execute / Assert
    with pytest.raises(ValueError, match="ollama thinking=off"):
        router_over(config, models)
