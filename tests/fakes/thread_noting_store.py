import threading

from fakes.store_factories import FreshStore

from stash.domain import Item, ItemType, Stage
from stash.store.port import DEFAULT_PAGE_SIZE


class ThreadNotingStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self.threads: list[int] = []

    def list_items(
        self,
        stage: Stage | None = None,
        item_type: ItemType | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Item]:
        self.threads.append(threading.get_ident())
        return super().list_items(stage, item_type, limit, offset)

    def get_setting(self, key: str) -> str | None:
        self.threads.append(threading.get_ident())
        return super().get_setting(key)

    def put_setting(self, key: str, value: str) -> None:
        self.threads.append(threading.get_ident())
        super().put_setting(key, value)
