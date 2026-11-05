import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from stash.capture import QUESTION_PREFIX, Reply
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.outbox import ReplySender

logger = logging.getLogger(__name__)

APOLOGY = Reply(
    "I couldn't pass that on to the assistant. "
    f"Send it again starting with {QUESTION_PREFIX} and I'll hand it over."
)


@dataclass(frozen=True, slots=True)
class Origin:
    chat: Chat

    def as_mapping(self) -> dict[str, str]:
        return {
            "platform": "telegram",
            "chat_id": self.chat.chat_id,
            "chat_type": "dm",
            "user_id": self.chat.user_id,
        }


class Assistant(Protocol):
    async def ask(self, text: str, chat: Chat) -> None: ...


class Inject(Protocol):
    def __call__(self, content: str, *, origin: Mapping[str, str]) -> bool: ...


class GatewayAssistant:
    def __init__(self, inject: Inject, sender: ReplySender) -> None:
        self._inject = inject
        self._sender = sender

    async def ask(self, text: str, chat: Chat) -> None:
        if not self._handed_over(text, chat):
            await self._sender.send(chat.chat_id, APOLOGY)

    def _handed_over(self, text: str, chat: Chat) -> bool:
        try:
            accepted = self._inject(text, origin=Origin(chat).as_mapping())
        except Exception:
            logger.warning("assistant injection failed for chat %s", chat.chat_id, exc_info=True)
            return False
        if not accepted:
            logger.warning("assistant injection refused for chat %s", chat.chat_id)
        return accepted
