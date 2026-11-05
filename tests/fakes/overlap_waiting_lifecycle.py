import threading

from stash.capture.ports import LifecycleActions
from stash.domain import Item, Outcome
from stash.lifecycle.results import Completion, ItemHistory


class OverlapWaitingLifecycle:
    def __init__(self, inner: LifecycleActions, grace_seconds: float) -> None:
        self._inner = inner
        self._grace_seconds = grace_seconds
        self._overlapped = threading.Event()
        self._arrivals = 0
        self._counting = threading.Lock()

    def history(self, item_id: str) -> ItemHistory:
        history = self._inner.history(item_id)
        if self._arrived_first():
            self._overlapped.wait(self._grace_seconds)
        else:
            self._overlapped.set()
        return history

    def complete(self, item_id: str) -> Completion:
        return self._inner.complete(item_id)

    def rate(self, outcome_id: str, rating: int) -> Outcome:
        return self._inner.rate(outcome_id, rating)

    def keep(self, item_id: str, kept: bool) -> Item:
        return self._inner.keep(item_id, kept)

    def _arrived_first(self) -> bool:
        with self._counting:
            self._arrivals += 1
            return self._arrivals == 1
