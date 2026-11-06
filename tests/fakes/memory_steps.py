import threading
from collections.abc import Sequence

from stash.domain import Step
from stash.store.port import DuplicateStepError


class MemorySteps:
    def __init__(self, lock: threading.RLock) -> None:
        self._lock = lock
        self._steps: dict[str, Step] = {}

    def replace_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        with self._lock:
            for step in steps:
                self._require_unowned_by_other_items(step)
            self.drop_steps_of(item_id)
            for step in steps:
                self._steps[step.id] = step

    def steps_for(self, item_id: str) -> list[Step]:
        with self._lock:
            steps = [step for step in self._steps.values() if step.item_id == item_id]
        return sorted(steps, key=lambda step: (step.position, step.id))

    def save_step(self, step: Step) -> None:
        with self._lock:
            self._require_unowned_by_other_items(step)
            self._steps[step.id] = step

    def get_step(self, step_id: str) -> Step | None:
        with self._lock:
            return self._steps.get(step_id)

    def open_confirmed_steps(self) -> list[Step]:
        with self._lock:
            open_steps = [step for step in self._steps.values() if step.confirmed and not step.done]
        return sorted(open_steps, key=lambda step: (step.item_id, step.position, step.id))

    def drop_steps_of(self, item_id: str) -> None:
        with self._lock:
            self._steps = {
                step_id: step for step_id, step in self._steps.items() if step.item_id != item_id
            }

    def _require_unowned_by_other_items(self, step: Step) -> None:
        holder = self._steps.get(step.id)
        if holder is not None and holder.item_id != step.item_id:
            raise DuplicateStepError(step.id)
