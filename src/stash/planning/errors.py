class PlanningError(Exception):
    pass


class UnknownItem(PlanningError):
    def __init__(self, item_id: str) -> None:
        super().__init__(f"no item {item_id!r}")
        self.item_id = item_id


class UnknownStep(PlanningError):
    def __init__(self, step_id: str) -> None:
        super().__init__(f"no step {step_id!r}")
        self.step_id = step_id


class PlanningRefused(PlanningError):
    pass
