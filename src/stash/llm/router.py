from collections.abc import Mapping, Sequence
from datetime import datetime
from types import MappingProxyType

from stash.config import LlmConfig, LlmTask, ModelChoice, ProviderName
from stash.llm.errors import LlmDeferred
from stash.llm.messages import ChatMessage
from stash.llm.port import BusyCheck, ChatModel

DEFERRED_REASON = "GPU busy; work deferred"


class DeferringModel:
    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        raise LlmDeferred(DEFERRED_REASON)


class ModelRouter:
    def __init__(
        self,
        config: LlmConfig,
        models: Mapping[ModelChoice, ChatModel],
        busy: BusyCheck,
    ) -> None:
        missing = sorted(str(choice) for choice in config.model_choices() if choice not in models)
        if missing:
            raise ValueError(f"no chat model for: {', '.join(missing)}")
        self._config = config
        self._models: Mapping[ModelChoice, ChatModel] = MappingProxyType(dict(models))
        self._busy = busy

    def model_for(self, task: LlmTask, now: datetime) -> ChatModel:
        choice = self._config.choice_for(task)
        if choice.provider is ProviderName.OLLAMA and self._busy.is_busy(now):
            return self._when_ollama_is_busy(choice)
        return self._models[choice]

    def _when_ollama_is_busy(self, choice: ModelChoice) -> ChatModel:
        if self._config.busy_fallback == "openrouter":
            return self._models[choice.with_provider(ProviderName.OPENROUTER)]
        return DeferringModel()
