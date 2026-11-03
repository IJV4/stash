import importlib
import logging
from collections.abc import Callable, Mapping, Sequence
from types import ModuleType

logger = logging.getLogger(__name__)

SECRET_SCOPE_MODULE = "agent.secret_scope"


def hermes_secret(
    name: str, import_module: Callable[[str], ModuleType] = importlib.import_module
) -> str | None:
    try:
        value = import_module(SECRET_SCOPE_MODULE).get_secret(name)
    except Exception as failure:
        logger.warning("could not read Hermes secret %s: %s", name, type(failure).__name__)
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def resolved_environment(
    base: Mapping[str, str],
    read_secret: Callable[[str], str | None],
    names: Sequence[str],
) -> dict[str, str]:
    secrets = {name: read_secret(name) for name in names}
    return {**base, **{name: value for name, value in secrets.items() if value is not None}}
