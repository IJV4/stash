from datetime import date

from stash.domain import Step


class RecordingStepPlanner:
    def __init__(self, step: Step, error: Exception | None = None) -> None:
        self._step = step
        self._error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    def add_step(
        self,
        item_id: str,
        text: str,
        *,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step:
        return self._record(
            "add_step", item_id=item_id, text=text, lead_days=lead_days, due_on=due_on
        )

    def edit_step(
        self,
        step_id: str,
        *,
        text: str | None = None,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step:
        return self._record(
            "edit_step", step_id=step_id, text=text, lead_days=lead_days, due_on=due_on
        )

    def complete_step(self, step_id: str) -> Step:
        return self._record("complete_step", step_id=step_id)

    def _record(self, name: str, **arguments: object) -> Step:
        self.calls.append((name, arguments))
        if self._error is not None:
            raise self._error
        return self._step
