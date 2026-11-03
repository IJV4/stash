from collections.abc import Mapping, Sequence
from datetime import datetime
from types import MappingProxyType

from stash.config import LlmConfig, LlmTask, ProviderName
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
        models: Mapping[ProviderName, ChatModel],
        busy: BusyCheck,
    ) -> None:
        missing = [name for name in config.providers if name not in models]
        if missing:
            raise ValueError(f"no chat model for configured provider(s): {', '.join(missing)}")
        self._config = config
        self._models: Mapping[ProviderName, ChatModel] = MappingProxyType(dict(models))
        self._busy = busy

    def model_for(self, task: LlmTask, now: datetime) -> ChatModel:
        provider = self._config.provider_for(task)
        if provider is ProviderName.OLLAMA and self._busy.is_busy(now):
            return self._when_ollama_is_busy()
        return self._models[provider]

    def _when_ollama_is_busy(self) -> ChatModel:
        if self._config.busy_fallback == "openrouter":
            return self._models[ProviderName.OPENROUTER]
        return DeferringModel()
