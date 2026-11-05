import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from stash.capture import IncomingMessage, forces_request
from stash.domain import SourceRef
from stash.hermes_adapter.owners import Owners

logger = logging.getLogger(__name__)

COMMAND_PREFIX = "/"
DISPATCH_HOOK = "pre_gateway_dispatch"


@dataclass(frozen=True, slots=True)
class Chat:
    chat_id: str
    user_id: str

    def __post_init__(self) -> None:
        for name, value in (("chat_id", self.chat_id), ("user_id", self.user_id)):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")


class Verdict(StrEnum):
    ALLOW = "allow"
    SKIP = "skip"

    def hook_result(self) -> dict[str, str]:
        return {"action": self.value}


class HermesSource(Protocol):
    @property
    def chat_id(self) -> str: ...

    @property
    def user_id(self) -> str | None: ...


class HermesEvent(Protocol):
    @property
    def text(self) -> str | None: ...

    @property
    def source(self) -> HermesSource: ...

    @property
    def message_id(self) -> str | None: ...

    @property
    def media_urls(self) -> Sequence[str] | None: ...

    @property
    def internal(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class Inbound:
    chat: Chat
    message: IncomingMessage

    @property
    def failure_verdict(self) -> Verdict:
        return Verdict.ALLOW if forces_request(self.message.text) else Verdict.SKIP


@dataclass(frozen=True, slots=True)
class Passthrough:
    pass


class EventTranslator:
    def __init__(
        self, owners: Owners, clock: Callable[[], datetime], new_id: Callable[[], str]
    ) -> None:
        self._owners = owners
        self._clock = clock
        self._new_id = new_id

    def read(self, event: HermesEvent) -> Inbound | Passthrough:
        chat = None if event.internal else self._owner_chat(event)
        text = event.text or ""
        if chat is None or text.strip().startswith(COMMAND_PREFIX):
            return Passthrough()
        message = self._message(event, chat, text)
        if not (message.text.strip() or message.media_paths):
            return Passthrough()
        return Inbound(chat, message)

    def _owner_chat(self, event: HermesEvent) -> Chat | None:
        user_id = event.source.user_id
        chat_id = event.source.chat_id
        if user_id is None or not self._owners.admits_user(user_id) or not chat_id.strip():
            return None
        return Chat(chat_id, user_id)

    def _message(self, event: HermesEvent, chat: Chat, text: str) -> IncomingMessage:
        source = SourceRef(chat.chat_id, event.message_id or self._new_id())
        media_paths = tuple(event.media_urls or ())
        try:
            return IncomingMessage(source, text, media_paths, self._clock())
        except ValueError:
            logger.warning("dropped %d media paths that stash refuses", len(media_paths))
            return IncomingMessage(source, text, (), self._clock())
