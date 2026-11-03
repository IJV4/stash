from collections.abc import Mapping
from pathlib import Path

import pytest

from stash.config import ConfigError, StashConfig
from stash.config.loader import load_config

KEY = "sk-env-secret"
HOME = "/home/u"
OLLAMA_TABLE = '[llm.ollama]\nmodel = "m"\n'
OPENROUTER_TABLE = '[llm.openrouter]\nmodel = "x"\n'
TASKS_TO_OPENROUTER = '[llm.tasks]\nsuggestions = "openrouter"\n'


def a_toml(
    top: str = "", provider: str = "ollama", llm_keys: str = "", tables: str = OLLAMA_TABLE
) -> str:
    return f'{top}\n[llm]\nprovider = "{provider}"\n{llm_keys}\n{tables}'


def with_key(**extra: str) -> dict[str, str]:
    return {"HOME": HOME, "OPENROUTER_API_KEY": KEY, **extra}


def without_key() -> dict[str, str]:
    return {"HOME": HOME}


def load(tmp_path: Path, text: str, env: Mapping[str, str] | None = None) -> StashConfig:
    path = tmp_path / "stash.toml"
    path.write_text(text, encoding="utf-8")
    return load_config(path, without_key() if env is None else env)


def load_message(tmp_path: Path, text: str, env: Mapping[str, str] | None = None) -> str:
    with pytest.raises(ConfigError) as error:
        load(tmp_path, text, env)
    return str(error.value)
