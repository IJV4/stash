from types import ModuleType


class InstalledModules:
    def __init__(self, *names: str) -> None:
        self._names = frozenset(names)

    def __call__(self, name: str) -> object | None:
        return ModuleType(name) if name in self._names else None
