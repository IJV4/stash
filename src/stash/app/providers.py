from collections.abc import Callable, Mapping

import httpx

from stash.config import LlmConfig, LlmTask, ModelChoice, ProviderName, ProviderSettings, Thinking
from stash.evaluation import EvalTarget, EvalTargets, NamedModel
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


def eval_chat_models(llm: LlmConfig, client: httpx.Client) -> dict[ModelChoice, ChatModel]:
    return _for_each_thinking(llm.providers, client, lambda settings: settings.model)


def vision_models(llm: LlmConfig, client: httpx.Client) -> dict[ModelChoice, ChatModel]:
    with_vision = {
        name: settings
        for name, settings in llm.providers.items()
        if settings.vision_model is not None
    }
    return _for_each_thinking(with_vision, client, lambda settings: settings.vision_model)


def _for_each_thinking(
    providers: Mapping[ProviderName, ProviderSettings],
    client: httpx.Client,
    model_of: Callable[[ProviderSettings], str | None],
) -> dict[ModelChoice, ChatModel]:
    return {
        ModelChoice(name, thinking): OpenAICompatibleChat(
            settings, client, model=model_of(settings), thinking=thinking
        )
        for name, settings in providers.items()
        for thinking in Thinking
    }


def own_vram_usage(llm: LlmConfig, client: httpx.Client) -> OwnVramUsage:
    settings = llm.providers.get(ProviderName.OLLAMA)
    return NoOwnVram() if settings is None else OllamaVramUsage(settings, client)


def model_unloader(llm: LlmConfig, client: httpx.Client) -> ModelUnloader:
    settings = llm.providers.get(ProviderName.OLLAMA)
    return NoModelToUnload() if settings is None else OllamaControl(settings, client)


def eval_targets(
    llm: LlmConfig,
    models: Mapping[ModelChoice, ChatModel],
    vision_by_choice: Mapping[ModelChoice, ChatModel],
) -> EvalTargets:
    return EvalTargets(
        tuple(
            _eval_target(choice, llm.providers[choice.provider], model, vision_by_choice)
            for choice, model in models.items()
        ),
        configured=llm.thinking_for(LlmTask.FILING),
    )


def _eval_target(
    choice: ModelChoice,
    settings: ProviderSettings,
    model: ChatModel,
    vision_by_choice: Mapping[ModelChoice, ChatModel],
) -> EvalTarget:
    return EvalTarget(
        choice=choice,
        text=NamedModel(settings.model, model),
        vision=_named_vision_model(choice, settings, vision_by_choice),
    )


def _named_vision_model(
    choice: ModelChoice,
    settings: ProviderSettings,
    vision_by_choice: Mapping[ModelChoice, ChatModel],
) -> NamedModel | None:
    if settings.vision_model is None:
        return None
    return NamedModel(settings.vision_model, vision_by_choice[choice])
