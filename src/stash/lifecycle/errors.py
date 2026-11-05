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


class LifecycleRefused(LifecycleError):
    pass
