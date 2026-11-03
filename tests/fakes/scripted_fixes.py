import threading

from stash.capture import Reply, Reroute
from stash.hermes_adapter.ports import FixApplier


class ScriptedFixes:
    def __init__(self, inner: FixApplier, failure: Exception | None = None) -> None:
        self._inner = inner
        self._failure = failure
        self.applied: list[str] = []
        self.threads: list[int] = []

    def apply(self, data: str) -> Reply | Reroute:
        self.applied.append(data)
        self.threads.append(threading.get_ident())
        if self._failure is not None:
            raise self._failure
        return self._inner.apply(data)
