from fakes.store_factories import FreshStore

from stash.domain import Item


class RacingItemStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self._saved_before_grouping: list[Item] = []

    def another_writer_saves_before_grouping(self, item: Item) -> None:
        self._saved_before_grouping.append(item)

    def group_item(self, child: Item, *, replacing: Item) -> None:
        for item in self._saved_before_grouping:
            self.save_item(item)
        self._saved_before_grouping.clear()
        super().group_item(child, replacing=replacing)
