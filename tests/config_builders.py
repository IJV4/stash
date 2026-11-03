from builders import an_ollama_settings

from stash.config import LlmConfig, ProviderName


def an_llm_config(**overrides: object) -> LlmConfig:
    fields: dict[str, object] = {
        "provider": ProviderName.OLLAMA,
        "busy_fallback": "wait",
        "providers": {ProviderName.OLLAMA: an_ollama_settings()},
        "tasks": {},
    }
    return LlmConfig(**{**fields, **overrides})
