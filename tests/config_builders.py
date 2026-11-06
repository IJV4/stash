import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from builders import an_ollama_settings, an_openrouter_settings

from stash.config import (
    GpuConfig,
    LlmConfig,
    NudgeConfig,
    ProviderName,
    ProviderSettings,
    StashConfig,
    Weekday,
)


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
        "nudges": NudgeConfig(),
    }
    return StashConfig(**{**fields, **overrides})


def a_nudge_config(**overrides: object) -> NudgeConfig:
    fields: dict[str, object] = {
        "digest_day": Weekday.SUNDAY,
        "digest_time": dt.time(10, 0),
        "reminder_time": dt.time(9, 0),
        "followup_time": dt.time(9, 0),
        "forgotten_after_days": 30,
        "stuck_doing_days": 21,
        "tick_seconds": 60,
    }
    return NudgeConfig(**{**fields, **overrides})
