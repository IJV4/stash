ITEM_CHANGED = "item {item_id!r} changed meanwhile; read it again and try again"
STASH_BUSY = "the stash is busy with another change; try again in a moment"


class LifecycleError(Exception):
    pass


class UnknownItem(LifecycleError):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"no item {item_id!r}")
        self.item_id = item_id


class UnknownOutcome(LifecycleError):
    def __init__(self, outcome_id: str) -> None:
        super().__init__(f"no outcome {outcome_id!r}")
        self.outcome_id = outcome_id


class ItemChanged(LifecycleError):
    def __init__(self, item_id: str) -> None:
        super().__init__(ITEM_CHANGED.format(item_id=item_id))
        self.item_id = item_id


class StashBusy(LifecycleError):
    def __init__(self) -> None:
        super().__init__(STASH_BUSY)


class LifecycleRefused(LifecycleError):
    pass
