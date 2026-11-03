from datetime import datetime

import pytest
from builders import BASE, LATER, an_ollama_settings, an_openrouter_settings
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel

from stash.config import (
    BusyFallback,
    LlmConfig,
    LlmTask,
    ProviderName,
)
from stash.llm import (
    ChatMessage,
    ChatModel,
    DeferringModel,
    LlmDeferred,
    LlmUnavailable,
    ModelRouter,
)

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
SCHEMA: dict[str, object] = {"type": "object"}
HELLO = [ChatMessage.text("user", "hello")]


def a_config(
    provider: ProviderName,
    busy_fallback: BusyFallback = "wait",
    tasks: dict[LlmTask, ProviderName] | None = None,
) -> LlmConfig:
    return LlmConfig(
        provider=provider,
        busy_fallback=busy_fallback,
        providers={
            OLLAMA: an_ollama_settings(),
            OPENROUTER: an_openrouter_settings(),
        },
        tasks=tasks or {},
    )


class Models:
    def __init__(self) -> None:
        self.ollama = FakeChatModel(reply={"from": "ollama"})
        self.openrouter = FakeChatModel(reply={"from": "openrouter"})

    def by_provider(self) -> dict[ProviderName, ChatModel]:
        return {OLLAMA: self.ollama, OPENROUTER: self.openrouter}


def routed(
    provider: ProviderName,
    *,
    busy: bool,
    busy_fallback: BusyFallback,
    task: LlmTask = LlmTask.FILING,
    tasks: dict[LlmTask, ProviderName] | None = None,
) -> tuple[ChatModel, Models]:
    models = Models()
    router = ModelRouter(
        a_config(provider, busy_fallback, tasks), models.by_provider(), FakeBusy(busy)
    )
    return router.model_for(task, BASE), models


def test_ollama_free_with_wait_fallback_routes_to_ollama() -> None:
    # Execute
    model, models = routed(OLLAMA, busy=False, busy_fallback="wait")

    # Assert
    assert model is models.ollama


def test_ollama_free_with_openrouter_fallback_routes_to_ollama() -> None:
    # Execute
    model, models = routed(OLLAMA, busy=False, busy_fallback="openrouter")

    # Assert
    assert model is models.ollama


def test_ollama_busy_with_wait_fallback_defers() -> None:
    # Setup
    model, _ = routed(OLLAMA, busy=True, busy_fallback="wait")

    # Execute / Assert
    with pytest.raises(LlmDeferred):
        model.complete_json(HELLO, SCHEMA, "filing")


def test_ollama_busy_with_wait_fallback_does_not_touch_either_provider() -> None:
    # Setup
    model, models = routed(OLLAMA, busy=True, busy_fallback="wait")

    # Execute
    with pytest.raises(LlmDeferred):
        model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert (models.ollama.calls, models.openrouter.calls) == ([], [])


def test_ollama_busy_with_openrouter_fallback_routes_to_openrouter() -> None:
    # Execute
    model, models = routed(OLLAMA, busy=True, busy_fallback="openrouter")

    # Assert
    assert model is models.openrouter


def test_openrouter_free_with_wait_fallback_routes_to_openrouter() -> None:
    # Execute
    model, models = routed(OPENROUTER, busy=False, busy_fallback="wait")

    # Assert
    assert model is models.openrouter


def test_openrouter_free_with_openrouter_fallback_routes_to_openrouter() -> None:
    # Execute
    model, models = routed(OPENROUTER, busy=False, busy_fallback="openrouter")

    # Assert
    assert model is models.openrouter


def test_openrouter_busy_with_wait_fallback_still_routes_to_openrouter() -> None:
    # Execute
    model, models = routed(OPENROUTER, busy=True, busy_fallback="wait")

    # Assert
    assert model is models.openrouter


def test_openrouter_busy_with_openrouter_fallback_routes_to_openrouter() -> None:
    # Execute
    model, models = routed(OPENROUTER, busy=True, busy_fallback="openrouter")

    # Assert
    assert model is models.openrouter


def test_a_task_override_routes_only_that_task_to_the_other_provider() -> None:
    # Execute
    model, models = routed(
        OLLAMA,
        busy=False,
        busy_fallback="wait",
        task=LlmTask.SUGGESTIONS,
        tasks={LlmTask.SUGGESTIONS: OPENROUTER},
    )

    # Assert
    assert model is models.openrouter


def test_a_task_without_an_override_uses_the_default_provider() -> None:
    # Execute
    model, models = routed(
        OLLAMA,
        busy=False,
        busy_fallback="wait",
        task=LlmTask.FILING,
        tasks={LlmTask.SUGGESTIONS: OPENROUTER},
    )

    # Assert
    assert model is models.ollama


def test_a_busy_gpu_defers_a_task_overridden_to_ollama() -> None:
    # Setup
    model, _ = routed(
        OPENROUTER,
        busy=True,
        busy_fallback="wait",
        task=LlmTask.SUGGESTIONS,
        tasks={LlmTask.SUGGESTIONS: OLLAMA},
    )

    # Execute / Assert
    with pytest.raises(LlmDeferred):
        model.complete_json(HELLO, SCHEMA, "filing")


def test_vision_is_routed_like_any_other_task() -> None:
    # Execute
    model, models = routed(
        OLLAMA,
        busy=False,
        busy_fallback="wait",
        task=LlmTask.VISION,
        tasks={LlmTask.VISION: OPENROUTER},
    )

    # Assert
    assert model is models.openrouter


def test_the_busy_check_is_asked_about_the_moment_given_to_model_for() -> None:
    # Setup
    class BusyAfter:
        def is_busy(self, now: datetime) -> bool:
            return now >= LATER

    router = ModelRouter(a_config(OLLAMA), Models().by_provider(), BusyAfter())

    # Execute
    model = router.model_for(LlmTask.FILING, LATER)

    # Assert
    assert isinstance(model, DeferringModel)


def test_a_router_without_a_model_for_every_configured_provider_raises_value_error() -> None:
    # Setup
    only_ollama: dict[ProviderName, ChatModel] = {OLLAMA: FakeChatModel()}

    # Execute / Assert
    with pytest.raises(ValueError, match="openrouter"):
        ModelRouter(a_config(OLLAMA), only_ollama, FakeBusy())


def test_a_router_ignores_later_changes_to_the_models_it_was_built_from() -> None:
    # Setup
    models = Models()
    by_provider = models.by_provider()
    router = ModelRouter(a_config(OLLAMA), by_provider, FakeBusy())

    # Execute
    by_provider[OLLAMA] = FakeChatModel()

    # Assert
    assert router.model_for(LlmTask.FILING, BASE) is models.ollama


def test_the_deferring_model_raises_llm_deferred_with_a_reason() -> None:
    # Execute / Assert
    with pytest.raises(LlmDeferred, match="GPU busy; work deferred"):
        DeferringModel().complete_json(HELLO, SCHEMA, "filing")


def test_a_deferred_call_can_be_handled_as_an_unavailable_provider() -> None:
    # Execute / Assert
    with pytest.raises(LlmUnavailable):
        DeferringModel().complete_json(HELLO, SCHEMA, "filing")
