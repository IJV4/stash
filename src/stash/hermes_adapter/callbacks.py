import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from stash.capture import Reply, Reroute
from stash.hermes_adapter.assistant import Assistant
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.outbox import Outbox
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.ports import FixApplier

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CallbackPress:
    chat: Chat
    message_id: str
    data: str
    done_rows: int = 0

    @property
    def is_on_a_batched_message(self) -> bool:
        return self.done_rows > 1


PressHandler = Callable[[CallbackPress], Awaitable[None]]


class FixCallbacks:
    def __init__(
        self, fixes: FixApplier, owners: Owners, outbox: Outbox, assistant: Assistant
    ) -> None:
        self._fixes = fixes
        self._owners = owners
        self._outbox = outbox
        self._assistant = assistant

    async def on_press(self, press: CallbackPress) -> None:
        if not self._owners.admits_user(press.chat.user_id):
            logger.info("ignoring a button press from a non-owner in chat %s", press.chat.chat_id)
            return
        try:
            await self._deliver(await asyncio.to_thread(self._fixes.apply, press.data), press)
        except Exception:
            logger.exception(
                "could not handle a button press on message %s in chat %s",
                press.message_id,
                press.chat.chat_id,
            )

    async def _deliver(self, outcome: Reply | Reroute, press: CallbackPress) -> None:
        match outcome:
            case Reply() if press.is_on_a_batched_message:
                await self._outbox.send(press.chat.chat_id, outcome)
            case Reply():
                await self._outbox.edit(press.chat.chat_id, press.message_id, outcome)
            case Reroute(text):
                await self._assistant.ask(text, press.chat)
