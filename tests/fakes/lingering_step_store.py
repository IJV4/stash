import threading
from collections.abc import Sequence

from fakes.memory_store import MemoryStore

from stash.domain import Step


class LingeringStepStore(MemoryStore):
    def __init__(self, grace_seconds: float) -> None:
        super().__init__()
        self.lingering = threading.Event()
        self._grace_seconds = grace_seconds
        self._armed = False
        self._someone_wrote = threading.Event()
        self._arming = threading.Lock()

    def linger_on_next_read(self) -> None:
        with self._arming:
            self._someone_wrote.clear()
            self._armed = True

    def steps_for(self, item_id: str) -> list[Step]:
        steps = super().steps_for(item_id)
        if self._disarmed():
            self.lingering.set()
            self._someone_wrote.wait(self._grace_seconds)
        return steps

    def save_steps(self, item_id: str, steps: Sequence[Step]) -> None:
        super().save_steps(item_id, steps)
        self._someone_wrote.set()

    def save_step(self, step: Step) -> None:
        super().save_step(step)
        self._someone_wrote.set()

    def _disarmed(self) -> bool:
        with self._arming:
            was_armed, self._armed = self._armed, False
            return was_armed
