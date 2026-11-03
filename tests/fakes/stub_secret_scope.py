from collections.abc import Mapping
from types import ModuleType

SECRET_SCOPE_MODULE = "agent.secret_scope"


class StubSecretScope:
    def __init__(self, secrets: Mapping[str, str | None], failure: Exception | None = None) -> None:
        self._secrets = dict(secrets)
        self._failure = failure
        self.requested: list[str] = []
        self.imported: list[str] = []

    def import_module(self, name: str) -> ModuleType:
        self.imported.append(name)
        module = ModuleType(name)
        module.get_secret = self._get_secret  # type: ignore[attr-defined]
        return module

    def _get_secret(self, secret_name: str) -> str | None:
        self.requested.append(secret_name)
        if self._failure is not None:
            raise self._failure
        return self._secrets.get(secret_name)


def importer_without_hermes(name: str) -> ModuleType:
    raise ImportError(f"No module named {name!r}")
