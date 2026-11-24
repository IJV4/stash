from stash.domain import Item, Stage
from stash.store.port import ItemStore

OPEN_STAGES = (Stage.INBOX, Stage.WANT_TO, Stage.PLANNED, Stage.DOING)
PER_STAGE_LIMIT = 40
ID_PREFIX_LENGTH = 12


def open_items(store: ItemStore) -> list[Item]:
    found = [
        item for stage in OPEN_STAGES for item in store.list_items(stage, limit=PER_STAGE_LIMIT)
    ]
    return sorted(found, key=lambda item: (item.created_at, item.id), reverse=True)


def id_prefix(item: Item) -> str:
    return item.id[:ID_PREFIX_LENGTH]


def open_item_with_prefix(store: ItemStore, prefix: str) -> Item | None:
    matching = [item for item in open_items(store) if item.id.startswith(prefix)]
    return matching[0] if len(matching) == 1 else None
