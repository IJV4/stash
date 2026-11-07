import threading

from stash.domain import Item, RawCapture
from stash.store.port import (
    ChildHoldsItemsError,
    ParentIsGroupedError,
    StaleItemError,
    UnknownCaptureError,
    UnknownItemError,
    require_parent,
    require_same_item,
)


class MemoryItemWrites:
    def __init__(
        self,
        lock: threading.RLock,
        captures: dict[str, RawCapture],
        items: dict[str, Item],
    ) -> None:
        self._lock = lock
        self._captures = captures
        self._items = items

    def save_item(self, item: Item) -> None:
        with self._lock:
            self._require_references(item)
            self._items[item.id] = item

    def update_item(self, item: Item, *, replacing: Item) -> None:
        with self._lock:
            self.require_replaceable(item, replacing)
            self._items[item.id] = item

    def group_item(self, child: Item, *, replacing: Item) -> None:
        parent_id = require_parent(child)
        with self._lock:
            self.require_replaceable(child, replacing)
            self._require_groupable_parent(parent_id)
            self._require_no_children(child.id)
            self._items[child.id] = child

    def require_replaceable(self, item: Item, replacing: Item) -> None:
        require_same_item(item, replacing)
        with self._lock:
            stored = self._items.get(item.id)
            if stored is None:
                raise UnknownItemError(item.id)
            if stored != replacing:
                raise StaleItemError(item.id)
            self._require_references(item)

    def put(self, item: Item) -> None:
        with self._lock:
            self._items[item.id] = item

    def _require_groupable_parent(self, parent_id: str) -> None:
        parent = self._items.get(parent_id)
        if parent is None:
            raise UnknownItemError(parent_id)
        if parent.parent_id is not None:
            raise ParentIsGroupedError(parent_id)

    def _require_no_children(self, item_id: str) -> None:
        if any(item.parent_id == item_id for item in self._items.values()):
            raise ChildHoldsItemsError(item_id)

    def _require_references(self, item: Item) -> None:
        if item.capture_id not in self._captures:
            raise UnknownCaptureError(item.capture_id)
        if item.parent_id is not None and item.parent_id not in self._items:
            raise UnknownItemError(item.parent_id)
