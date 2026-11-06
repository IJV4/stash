from collections.abc import Sequence

from fakes.memory_store import MemoryStore

from stash.domain import Step


class WatchedStepStore(MemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.step_writes = 0
        self._vanish_before_write: str | None = None
        self._write_error: Exception | None = None

    def vanish_before_next_step_write(self, item_id: str) -> None:
        self._vanish_before_write = item_id

    def fail_step_writes_with(self, error: Exception) -> None:
        self._write_error = error

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        self._before_write()
        super().save_steps(item_id, steps)

    def save_step(self, step: Step) -> None:
        self._before_write()
        super().save_step(step)

    def _before_write(self) -> None:
        self.step_writes += 1
        if self._write_error is not None:
            raise self._write_error
        if self._vanish_before_write is not None:
            self.delete_item(self._vanish_before_write)
            self._vanish_before_write = None
