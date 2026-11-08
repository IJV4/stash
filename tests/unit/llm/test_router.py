import pytest
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from router_builders import a_router_config, default_thinking_models

from stash.config import (
    ProviderName,
)
from stash.llm import (
    ChatMessage,
    ChatModel,
    ModelRouter,
)

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
SCHEMA: dict[str, object] = {"type": "object"}
HELLO = [ChatMessage.text("user", "hello")]


def test_a_router_without_a_model_for_every_configured_provider_raises_value_error() -> None:
    # Setup
    only_ollama: dict[ProviderName, ChatModel] = {OLLAMA: FakeChatModel()}

    # Execute / Assert
    with pytest.raises(ValueError, match="openrouter"):
        ModelRouter(a_router_config(OLLAMA), default_thinking_models(only_ollama), FakeBusy())
