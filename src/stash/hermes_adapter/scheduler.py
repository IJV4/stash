import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class Scheduler(Protocol):
    def now(self) -> datetime: ...

    async def pause(self, seconds: float) -> None: ...

    def spawn(self, coro: Coroutine[Any, Any, None], name: str) -> None: ...


class LoopScheduler:
    def __init__(
        self,
        clock: Callable[[], datetime],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._tasks: set[asyncio.Task[None]] = set()

    def now(self) -> datetime:
        return self._clock()

    async def pause(self, seconds: float) -> None:
        await self._sleep(seconds)

    def spawn(self, coro: Coroutine[Any, Any, None], name: str) -> None:
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._finished)

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.wait(tuple(self._tasks))

    def _finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and (failure := task.exception()) is not None:
            logger.error("task %s failed", task.get_name(), exc_info=failure)
