from collections.abc import Mapping
from pathlib import Path

from stash.config import ConfigError

CONFIG_VARIABLE = "STASH_CONFIG"
HOME_VARIABLE = "HOME"
DEFAULT_RELATIVE_PATH = Path(".config/stash/stash.toml")


def config_path(option: str | None, env: Mapping[str, str]) -> Path:
    if option is not None:
        return Path(option)
    named = env.get(CONFIG_VARIABLE)
    if named:
        return Path(named)
    home = env.get(HOME_VARIABLE)
    if home:
        return Path(home) / DEFAULT_RELATIVE_PATH
    raise ConfigError(f"cannot locate the config file: pass --config, or set {CONFIG_VARIABLE}")
