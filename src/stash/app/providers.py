from collections.abc import Mapping

import httpx

from stash.config import LlmConfig, LlmTask, ModelChoice, ProviderName
from stash.evaluation import EvalTarget
from stash.gpu import NoOwnVram, OwnVramUsage
from stash.llm import ChatModel, ModelUnloader, NoModelToUnload
from stash.llm.openai_compat import OpenAICompatibleChat
from stash.llm.probes import OllamaControl, OllamaVramUsage


def chat_models(llm: LlmConfig, client: httpx.Client) -> dict[ModelChoice, ChatModel]:
    return {
        choice: OpenAICompatibleChat(
            llm.providers[choice.provider], client, thinking=choice.thinking
        )
        for choice in llm.model_choices()
    }


def own_vram_usage(llm: LlmConfig, client: httpx.Client) -> OwnVramUsage:
    settings = llm.providers.get(ProviderName.OLLAMA)
    return NoOwnVram() if settings is None else OllamaVramUsage(settings, client)


def model_unloader(llm: LlmConfig, client: httpx.Client) -> ModelUnloader:
    settings = llm.providers.get(ProviderName.OLLAMA)
    return NoModelToUnload() if settings is None else OllamaControl(settings, client)


def eval_targets(
    llm: LlmConfig, client: httpx.Client, models: Mapping[ModelChoice, ChatModel]
) -> dict[ProviderName, EvalTarget]:
    return {
        name: EvalTarget(
            label=f"{name}:{settings.model}",
            model=models[llm.choice_for(LlmTask.FILING).with_provider(name)],
            vision_model=(
                None
                if settings.vision_model is None
                else OpenAICompatibleChat(
                    settings,
                    client,
                    model=settings.vision_model,
                    thinking=llm.thinking_for(LlmTask.VISION),
                )
            ),
        )
        for name, settings in llm.providers.items()
    }
