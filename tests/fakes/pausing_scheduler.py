import asyncio
from collections.abc import Callable, Coroutine, Sequence
from datetime import datetime, timedelta
from typing import Any

from builders import BASE

MAX_PAUSES = 200


class PausingScheduler:
    def __init__(
        self,
        advances: Sequence[float] = (),
        on_pause: Callable[[], None] | None = None,
        start: datetime = BASE,
    ) -> None:
        self._now = start
        self._advances = list(advances)
        self._on_pause = on_pause
        self._waiting: list[Coroutine[Any, Any, None]] = []
        self.requested: list[float] = []
        self.spawned: list[str] = []
        self.failures: list[BaseException] = []

    def now(self) -> datetime:
        return self._now

    async def pause(self, seconds: float) -> None:
        if len(self.requested) >= MAX_PAUSES:
            raise RuntimeError("paused too often: a flush is waiting for a batch that never comes")
        self.requested.append(seconds)
        advance = self._advances.pop(0) if self._advances else seconds
        self._now += timedelta(seconds=advance)
        if self._on_pause is not None:
            hook, self._on_pause = self._on_pause, None
            hook()

    def spawn(self, coro: Coroutine[Any, Any, None], name: str) -> None:
        self.spawned.append(name)
        self._waiting.append(coro)

    def abandon(self) -> None:
        for coro in self._waiting:
            coro.close()
        self._waiting = []

    async def drain(self) -> None:
        while self._waiting:
            wave, self._waiting = self._waiting, []
            outcomes = await asyncio.gather(*wave, return_exceptions=True)
            self.failures.extend(o for o in outcomes if isinstance(o, BaseException))
