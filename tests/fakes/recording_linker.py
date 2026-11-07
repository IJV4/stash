from stash.domain import Item


class RecordingLinker:
    def __init__(self) -> None:
        self.linked: list[Item] = []

    def link(self, item: Item) -> None:
        self.linked.append(item)
