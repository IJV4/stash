from collections.abc import Callable, Mapping
from typing import Any

from fakes.store_factories import FreshStore

from stash.store import StoreBusyError

_OWN_ATTRIBUTES = frozenset({"fail_on", "fail_next", "calls", "record"})


class StoreFault(Exception):
    pass


class FaultyStore(FreshStore):
    def __init__(
        self,
        *,
        fail_on: Mapping[str, BaseException] | None = None,
        fail_once: Mapping[str, BaseException] | None = None,
        record: bool = False,
    ) -> None:
        self.fail_on: dict[str, BaseException] = dict(fail_on or {})
        self._once: dict[str, BaseException] = dict(fail_once or {})
        self.calls: list[str] = []
        self.record = record
        super().__init__()

    def fail_next(self, name: str, error: BaseException) -> None:
        self._once[name] = error

    def __getattribute__(self, name: str) -> Any:
        attribute = super().__getattribute__(name)
        if name.startswith("_") or name in _OWN_ATTRIBUTES or not callable(attribute):
            return attribute
        return self._watched(name, attribute)

    def _watched(self, name: str, method: Callable[..., Any]) -> Callable[..., Any]:
        def call(*args: Any, **kwargs: Any) -> Any:
            if self.record:
                self.calls.append(name)
            fault = self._once.pop(name, None) or self.fail_on.get(name)
            if fault is not None:
                raise fault
            return method(*args, **kwargs)

        return call


BUSY_WRITES = ("update_item", "record_completion", "group_item", "save_steps")
CLOSED = "database is closed"


def busy_store() -> FaultyStore:
    return FaultyStore(fail_on={name: StoreBusyError() for name in BUSY_WRITES})


def unreadable_store() -> FaultyStore:
    return FaultyStore(fail_on={"get_item": StoreFault(CLOSED), "library": StoreFault(CLOSED)})


def unlistable_store() -> FaultyStore:
    return FaultyStore(fail_on={"list_items": StoreFault(CLOSED)})


STEP_WRITES = ("save_steps", "save_step")


def step_writes(store: FaultyStore) -> int:
    return sum(store.calls.count(name) for name in STEP_WRITES)
