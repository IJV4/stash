import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, Protocol

from stash.capture import Reply
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.scheduler import Scheduler

logger = logging.getLogger(__name__)

SEND_TIMEOUT_S = 30.0
NUDGE_DELIVERY_FAILED_LOG = "nudge delivery failed; the next tick tries again"
PROPOSAL_DELIVERY_FAILED_LOG = "proposal delivery failed; the next tick tries again"
TICKER_ALREADY_RUNNING_LOG = "the ticker is already running; reusing it"

Send = Callable[[Reply], None]
Spawn = Callable[[Coroutine[Any, Any, None]], object]


class NudgeDeliveries(Protocol):
    def deliver(self, now: datetime, send: Send) -> None: ...


class ProposalDeliveries(Protocol):
    def deliver(self, send: Send) -> None: ...


class Ticker:
    def __init__(
        self,
        nudges: NudgeDeliveries,
        proposals: ProposalDeliveries,
        sender: ReplySender,
        owner_chat: str,
        scheduler: Scheduler,
        interval_s: float,
        send_timeout_s: float = SEND_TIMEOUT_S,
    ) -> None:
        self._nudges = nudges
        self._proposals = proposals
        self._sender = sender
        self._owner_chat = owner_chat
        self._scheduler = scheduler
        self._interval_s = interval_s
        self._send_timeout_s = send_timeout_s
        self._one_tick_at_a_time = asyncio.Lock()

    async def tick(self) -> None:
        async with self._one_tick_at_a_time:
            send = self._send_from_worker_thread(asyncio.get_running_loop())
            await self._deliver(
                NUDGE_DELIVERY_FAILED_LOG, self._nudges.deliver, self._scheduler.now(), send
            )
            await self._deliver(PROPOSAL_DELIVERY_FAILED_LOG, self._proposals.deliver, send)

    async def run_forever(self) -> None:
        while True:
            await self.tick()
            await self._scheduler.pause(self._interval_s)

    async def _deliver(
        self, failure_log: str, delivery: Callable[..., None], *arguments: Any
    ) -> None:
        try:
            await asyncio.to_thread(delivery, *arguments)
        except Exception:
            logger.exception(failure_log)

    def _send_from_worker_thread(self, loop: asyncio.AbstractEventLoop) -> Send:
        def send(reply: Reply) -> None:
            sending = asyncio.run_coroutine_threadsafe(
                self._sender.send(self._owner_chat, reply), loop
            )
            try:
                sending.result(timeout=self._send_timeout_s)
            except BaseException:
                sending.cancel()
                raise

        return send


class TickerLauncher:
    def __init__(self) -> None:
        self._running = False

    def start_once(self, spawn: Spawn, make: Callable[[], Ticker]) -> None:
        if self._running:
            logger.info(TICKER_ALREADY_RUNNING_LOG)
            return
        supervised = self._supervised(make())
        self._running = True
        try:
            spawn(supervised)
        except BaseException:
            supervised.close()
            self._running = False
            raise

    async def _supervised(self, ticker: Ticker) -> None:
        try:
            await ticker.run_forever()
        finally:
            self._running = False
