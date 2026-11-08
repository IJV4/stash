from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SentMessage:
    chat_id: str
    text: str
    reply_markup: Any


@dataclass(frozen=True, slots=True)
class EditedMessage:
    text: str
    chat_id: str
    message_id: int
    reply_markup: Any


@dataclass(frozen=True, slots=True)
class SentDocument:
    chat_id: str
    document: Any
    filename: str
    caption: str | None


class FakeTelegramBot:
    def __init__(self) -> None:
        self.sent: list[SentMessage] = []
        self.edited: list[EditedMessage] = []
        self.documents: list[SentDocument] = []

    async def send_message(self, chat_id: str, text: str, reply_markup: Any = None) -> None:
        self.sent.append(SentMessage(chat_id, text, reply_markup))

    async def edit_message_text(
        self, text: str, chat_id: str, message_id: int, reply_markup: Any = None
    ) -> None:
        self.edited.append(EditedMessage(text, chat_id, message_id, reply_markup))

    async def send_document(
        self, *, chat_id: str, document: Any, filename: str, caption: str | None = None
    ) -> None:
        self.documents.append(SentDocument(chat_id, document, filename, caption))


class FakeTelegramApplication:
    def __init__(self) -> None:
        self.bot = FakeTelegramBot()
        self.handlers: list[Any] = []

    def add_handler(self, handler: Any, group: int = 0) -> None:
        self.handlers.append(handler)
