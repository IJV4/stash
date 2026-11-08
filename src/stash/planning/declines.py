from stash.domain import Item
from stash.store.port import SettingsStore

_KEY_TEMPLATE = "planning.declined:{item_id}"


class Declines:
    def __init__(self, settings: SettingsStore) -> None:
        self._settings = settings

    def is_declined(self, item: Item) -> bool:
        if item.date is None:
            return False
        return self._settings.get_setting(self._key(item)) == item.date.isoformat()

    def record(self, item: Item) -> None:
        if item.date is not None:
            self._settings.put_setting(self._key(item), item.date.isoformat())

    @staticmethod
    def _key(item: Item) -> str:
        return _KEY_TEMPLATE.format(item_id=item.id)
