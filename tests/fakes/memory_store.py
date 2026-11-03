import threading

from stash.domain import CaptureStatus, Item, ItemType, RawCapture, SourceRef, Stage
from stash.store.port import DEFAULT_PAGE_SIZE, UnknownCaptureError, require_non_negative


class MemoryStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._captures: dict[str, RawCapture] = {}
        self._sources: set[SourceRef] = set()
        self._items: dict[str, Item] = {}
        self._settings: dict[str, str] = {}

    def add_capture(self, capture: RawCapture) -> bool:
        with self._lock:
            if capture.source in self._sources:
                return False
            if capture.id in self._captures:
                raise ValueError(f"capture id {capture.id!r} already exists")
            self._captures[capture.id] = capture
            self._sources.add(capture.source)
            return True

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None:
        with self._lock:
            self._captures[capture_id] = self._known_capture(capture_id).with_status(status)

    def get_capture(self, capture_id: str) -> RawCapture | None:
        with self._lock:
            return self._captures.get(capture_id)

    def pending_captures(self) -> list[RawCapture]:
        with self._lock:
            pending = [
                capture
                for capture in self._captures.values()
                if capture.status is CaptureStatus.PENDING
            ]
        return sorted(pending, key=lambda capture: (capture.received_at, capture.id))

    def save_item(self, item: Item) -> None:
        with self._lock:
            self._known_capture(item.capture_id)
            self._items[item.id] = item

    def get_item(self, item_id: str) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def delete_item(self, item_id: str) -> None:
        with self._lock:
            self._items.pop(item_id, None)

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        require_non_negative("limit", limit)
        require_non_negative("offset", offset)
        matching = [
            item
            for item in self._newest_first()
            if (stage is None or item.stage is stage)
            and (item_type is None or item.item_type is item_type)
        ]
        return matching[offset : offset + limit]

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]:
        require_non_negative("limit", limit)
        if not query.strip():
            return []
        needle = query.casefold()
        matching = [item for item in self._newest_first() if _mentions(item, needle)]
        return matching[:limit]

    def get_setting(self, key: str) -> str | None:
        with self._lock:
            return self._settings.get(key)

    def put_setting(self, key: str, value: str) -> None:
        with self._lock:
            self._settings[key] = value

    def _known_capture(self, capture_id: str) -> RawCapture:
        capture = self._captures.get(capture_id)
        if capture is None:
            raise UnknownCaptureError(capture_id)
        return capture

    def _newest_first(self) -> list[Item]:
        with self._lock:
            items = list(self._items.values())
        return sorted(items, key=lambda item: (item.created_at, item.id), reverse=True)


def _mentions(item: Item, needle: str) -> bool:
    return any(needle in text.casefold() for text in (item.title, item.note, *item.tags))
