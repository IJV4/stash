from typing import Protocol

from stash.domain import CaptureStatus, Item, ItemType, RawCapture, Stage

DEFAULT_PAGE_SIZE = 20


class UnknownCaptureError(Exception):
    pass


def require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must not be negative")


class CaptureStore(Protocol):
    def add_capture(self, capture: RawCapture) -> bool: ...

    def set_capture_status(self, capture_id: str, status: CaptureStatus) -> None: ...

    def get_capture(self, capture_id: str) -> RawCapture | None: ...

    def pending_captures(self) -> list[RawCapture]: ...


class ItemStore(Protocol):
    def save_item(self, item: Item) -> None: ...

    def get_item(self, item_id: str) -> Item | None: ...

    def delete_item(self, item_id: str) -> None: ...

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]: ...

    def search_items(self, query: str, limit: int = DEFAULT_PAGE_SIZE) -> list[Item]: ...


class SettingsStore(Protocol):
    def get_setting(self, key: str) -> str | None: ...

    def put_setting(self, key: str, value: str) -> None: ...


class Store(CaptureStore, ItemStore, SettingsStore, Protocol): ...
