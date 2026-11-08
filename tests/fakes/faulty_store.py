from collections.abc import Callable, Mapping
from typing import Any

from fakes.store_factories import FreshStore

_OWN_ATTRIBUTES = frozenset({"fail_on", "calls", "record"})


class FaultyStore(FreshStore):
    def __init__(
        self, *, fail_on: Mapping[str, BaseException] | None = None, record: bool = False
    ) -> None:
        self.fail_on: dict[str, BaseException] = dict(fail_on or {})
        self.calls: list[str] = []
        self.record = record
        super().__init__()

    def __getattribute__(self, name: str) -> Any:
        attribute = super().__getattribute__(name)
        if name.startswith("_") or name in _OWN_ATTRIBUTES or not callable(attribute):
            return attribute
        return self._watched(name, attribute)

    def _watched(self, name: str, method: Callable[..., Any]) -> Callable[..., Any]:
        def call(*args: Any, **kwargs: Any) -> Any:
            if self.record:
                self.calls.append(name)
            fault = self.fail_on.get(name)
            if fault is not None:
                raise fault
            return method(*args, **kwargs)

        return call
