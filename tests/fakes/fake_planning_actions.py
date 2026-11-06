from stash.domain import Step
from stash.planning.errors import PlanningError


class FakePlanningActions:
    def __init__(self, steps: tuple[Step, ...] = (), error: PlanningError | None = None) -> None:
        self._steps = steps
        self._error = error

    def confirm_all(self, item_id: str) -> tuple[Step, ...]:
        self._fail_if_scripted()
        return self._steps

    def discard(self, item_id: str) -> None:
        self._fail_if_scripted()

    def complete_step(self, step_id: str) -> Step:
        self._fail_if_scripted()
        return self._steps[0]

    def _fail_if_scripted(self) -> None:
        if self._error is not None:
            raise self._error
