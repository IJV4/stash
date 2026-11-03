import logging
from collections.abc import Callable

from stash.capture import BurstCoalescer, Deferred, Filed, Reply
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.scheduler import Scheduler

logger = logging.getLogger(__name__)

RECHECK_SECONDS = 0.05


class ChatBurst:
    def __init__(
        self, coalescer: BurstCoalescer, chat_id: str, sender: ReplySender, scheduler: Scheduler
    ) -> None:
        self._coalescer = coalescer
        self._chat_id = chat_id
        self._sender = sender
        self._scheduler = scheduler
        self._flushing = False

    def add(self, result: Filed | Deferred) -> None:
        self._coalescer.add(result, self._scheduler.now())
        if not self._flushing:
            self._flushing = True
            self._scheduler.spawn(self._flush(), f"stash-burst-{self._chat_id}")

    async def _flush(self) -> None:
        try:
            reply = await self._ripe_reply()
        finally:
            self._flushing = False
        await self._deliver(reply)

    async def _ripe_reply(self) -> Reply:
        await self._scheduler.pause(self._coalescer.window_seconds)
        while (reply := self._coalescer.due(self._scheduler.now())) is None:
            await self._scheduler.pause(RECHECK_SECONDS)
        return reply

    async def _deliver(self, reply: Reply) -> None:
        try:
            await self._sender.send(self._chat_id, reply)
        except Exception:
            logger.exception("could not send the burst reply to chat %s", self._chat_id)


class Bursts:
    def __init__(
        self,
        factory: Callable[[], BurstCoalescer],
        sender: ReplySender,
        scheduler: Scheduler,
    ) -> None:
        self._factory = factory
        self._sender = sender
        self._scheduler = scheduler
        self._chats: dict[str, ChatBurst] = {}

    def add(self, chat_id: str, result: Filed | Deferred) -> None:
        if chat_id not in self._chats:
            self._chats[chat_id] = ChatBurst(
                self._factory(), chat_id, self._sender, self._scheduler
            )
        self._chats[chat_id].add(result)
