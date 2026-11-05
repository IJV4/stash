from pathlib import Path
from zoneinfo import ZoneInfo

from builders import an_ollama_settings, an_openrouter_settings

from stash.config import GpuConfig, LlmConfig, ProviderName, ProviderSettings, StashConfig


def both_providers() -> dict[ProviderName, ProviderSettings]:
    return {
        ProviderName.OLLAMA: an_ollama_settings(),
        ProviderName.OPENROUTER: an_openrouter_settings(),
    }


def an_llm_config(**overrides: object) -> LlmConfig:
    fields: dict[str, object] = {
        "provider": ProviderName.OLLAMA,
        "busy_fallback": "wait",
        "providers": {ProviderName.OLLAMA: an_ollama_settings()},
        "tasks": {},
    }
    return LlmConfig(**{**fields, **overrides})


def a_stash_config(**overrides: object) -> StashConfig:
    fields: dict[str, object] = {
        "data_dir": Path("/data/stash"),
        "timezone": ZoneInfo("America/Los_Angeles"),
        "llm": an_llm_config(),
        "gpu": GpuConfig(),
    }
    return StashConfig(**{**fields, **overrides})
