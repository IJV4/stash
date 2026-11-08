from typing import Protocol

from stash.capture import Reply


class ReplySender(Protocol):
    async def send(self, chat_id: str, reply: Reply) -> None: ...


class FileSender(Protocol):
    async def send_file(self, chat_id: str, filename: str, data: bytes, caption: str) -> None: ...


class Outbox(ReplySender, FileSender, Protocol):
    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None: ...


class OutboxUnavailable(Exception):
    pass


class _UnavailableOutbox:
    async def send(self, chat_id: str, reply: Reply) -> None:
        raise OutboxUnavailable("the Telegram connection is not up yet")

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        raise OutboxUnavailable("the Telegram connection is not up yet")

    async def send_file(self, chat_id: str, filename: str, data: bytes, caption: str) -> None:
        raise OutboxUnavailable("the Telegram connection is not up yet")


class LateBoundOutbox:
    def __init__(self) -> None:
        self._outbox: Outbox = _UnavailableOutbox()

    def bind(self, outbox: Outbox) -> None:
        self._outbox = outbox

    async def send(self, chat_id: str, reply: Reply) -> None:
        await self._outbox.send(chat_id, reply)

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        await self._outbox.edit(chat_id, message_id, reply)

    async def send_file(self, chat_id: str, filename: str, data: bytes, caption: str) -> None:
        await self._outbox.send_file(chat_id, filename, data, caption)
