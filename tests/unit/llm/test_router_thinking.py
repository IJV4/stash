import pytest
from builders import BASE
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from router_builders import a_router_config

from stash.config import (
    BusyFallback,
    LlmConfig,
    LlmTask,
    ModelChoice,
    ProviderName,
    Thinking,
)
from stash.llm import ChatMessage, ChatModel, LlmDeferred, ModelRouter

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
DEFAULT = Thinking.DEFAULT
OFF = Thinking.OFF
SCHEMA: dict[str, object] = {"type": "object"}
HELLO = [ChatMessage.text("user", "hello")]
FILING_OFF = {LlmTask.FILING: OFF}

ROUTING_TABLE = [
    (OLLAMA, False, "wait", ModelChoice(OLLAMA, OFF)),
    (OLLAMA, False, "openrouter", ModelChoice(OLLAMA, OFF)),
    (OLLAMA, True, "wait", None),
    (OLLAMA, True, "openrouter", ModelChoice(OPENROUTER, OFF)),
    (OPENROUTER, False, "wait", ModelChoice(OPENROUTER, OFF)),
    (OPENROUTER, True, "wait", ModelChoice(OPENROUTER, OFF)),
]
ROUTING_IDS = [
    "ollama-free-wait",
    "ollama-free-openrouter",
    "ollama-busy-wait-defers",
    "ollama-busy-openrouter-reroutes-keeping-off",
    "openrouter-free-wait",
    "openrouter-busy-wait",
]


def models_for(config: LlmConfig) -> dict[ModelChoice, FakeChatModel]:
    return {choice: FakeChatModel() for choice in config.model_choices()}


def router_over(
    config: LlmConfig, models: dict[ModelChoice, FakeChatModel], busy: bool = False
) -> ModelRouter:
    chat_models: dict[ModelChoice, ChatModel] = dict(models)
    return ModelRouter(config, chat_models, FakeBusy(busy))


def choice_of(model: ChatModel, models: dict[ModelChoice, FakeChatModel]) -> ModelChoice | None:
    return next((choice for choice, known in models.items() if known is model), None)


@pytest.mark.parametrize(
    ("provider", "busy", "busy_fallback", "expected"), ROUTING_TABLE, ids=ROUTING_IDS
)
def test_filing_with_thinking_off_is_routed_by_provider_and_busy_fallback(
    provider: ProviderName,
    busy: bool,
    busy_fallback: BusyFallback,
    expected: ModelChoice | None,
) -> None:
    # Setup
    config = a_router_config(provider, busy_fallback, thinking=FILING_OFF)
    models = models_for(config)
    router = router_over(config, models, busy)

    # Execute
    model = router.model_for(LlmTask.FILING, BASE)

    # Assert
    assert choice_of(model, models) == expected


def test_a_deferred_filing_with_thinking_off_raises_llm_deferred() -> None:
    # Setup
    config = a_router_config(OLLAMA, "wait", thinking=FILING_OFF)
    router = router_over(config, models_for(config), busy=True)
    model = router.model_for(LlmTask.FILING, BASE)

    # Execute / Assert
    with pytest.raises(LlmDeferred):
        model.complete_json(HELLO, SCHEMA, "filing")


def test_a_task_left_at_default_gets_the_default_model_while_another_is_off() -> None:
    # Setup
    config = a_router_config(thinking=FILING_OFF)
    models = models_for(config)

    # Execute
    model = router_over(config, models).model_for(LlmTask.SUGGESTIONS, BASE)

    # Assert
    assert model is models[ModelChoice(OLLAMA, DEFAULT)]


def test_vision_does_not_inherit_the_filing_setting() -> None:
    # Setup
    config = a_router_config(thinking=FILING_OFF)
    models = models_for(config)

    # Execute
    model = router_over(config, models).model_for(LlmTask.VISION, BASE)

    # Assert
    assert model is models[ModelChoice(OLLAMA, DEFAULT)]


def test_vision_with_its_own_thinking_off_gets_the_off_model() -> None:
    # Setup
    config = a_router_config(thinking={LlmTask.VISION: OFF})
    models = models_for(config)

    # Execute
    model = router_over(config, models).model_for(LlmTask.VISION, BASE)

    # Assert
    assert model is models[ModelChoice(OLLAMA, OFF)]


def test_a_router_without_a_model_for_a_choice_the_config_uses_names_it() -> None:
    # Setup
    config = a_router_config(thinking=FILING_OFF)
    models = models_for(config)
    del models[ModelChoice(OLLAMA, OFF)]

    # Execute / Assert
    with pytest.raises(ValueError, match="ollama thinking=off"):
        router_over(config, models)


def test_a_router_does_not_demand_a_model_for_a_thinking_value_no_task_uses() -> None:
    # Setup
    config = a_router_config()
    models = models_for(config)
    assert ModelChoice(OLLAMA, OFF) not in models

    # Execute
    model = router_over(config, models).model_for(LlmTask.FILING, BASE)

    # Assert
    assert model is models[ModelChoice(OLLAMA, DEFAULT)]


def test_a_busy_ollama_reroutes_a_default_task_to_the_openrouter_default_model() -> None:
    # Setup
    config = a_router_config(OLLAMA, "openrouter", thinking={LlmTask.VISION: OFF})
    models = models_for(config)
    router = router_over(config, models, busy=True)

    # Execute
    model = router.model_for(LlmTask.FILING, BASE)

    # Assert
    assert model is models[ModelChoice(OPENROUTER, DEFAULT)]
