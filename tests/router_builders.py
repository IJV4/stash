from collections.abc import Mapping

from config_builders import an_llm_config, both_providers

from stash.config import BusyFallback, LlmConfig, LlmTask, ModelChoice, ProviderName, Thinking
from stash.llm import ChatModel


def a_router_config(
    provider: ProviderName = ProviderName.OLLAMA,
    busy_fallback: BusyFallback = "wait",
    tasks: dict[LlmTask, ProviderName] | None = None,
    thinking: dict[LlmTask, Thinking] | None = None,
) -> LlmConfig:
    return an_llm_config(
        provider=provider,
        busy_fallback=busy_fallback,
        providers=both_providers(),
        tasks=tasks or {},
        thinking=thinking or {},
    )


def default_thinking_models(
    by_provider: Mapping[ProviderName, ChatModel],
) -> dict[ModelChoice, ChatModel]:
    return {
        ModelChoice(provider, Thinking.DEFAULT): model for provider, model in by_provider.items()
    }
