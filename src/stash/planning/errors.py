PLANNING_BUSY = "the stash is busy with another change; try again in a moment"
PROPOSAL_UNUSABLE = "the step model gave no usable steps"


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


class PlanningBusy(PlanningError):
    def __init__(self) -> None:
        super().__init__(PLANNING_BUSY)


class ProposalUnusable(PlanningRefused):
    def __init__(self) -> None:
        super().__init__(PROPOSAL_UNUSABLE)
