from collections.abc import Mapping


class FakeSearchPath:
    def __init__(self, executables: Mapping[str, str] | None = None) -> None:
        self._executables = dict(executables or {})

    def __call__(self, name: str) -> str | None:
        return self._executables.get(name)
