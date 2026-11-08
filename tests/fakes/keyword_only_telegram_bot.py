from typing import Any


class KeywordOnlyTelegramBot:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def send_message(self, *, chat_id: str, text: str, reply_markup: Any = None) -> None:
        self.calls.append(
            ("send", {"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        )

    async def edit_message_text(
        self, *, text: str, chat_id: str, message_id: int, reply_markup: Any = None
    ) -> None:
        self.calls.append(
            (
                "edit",
                {
                    "text": text,
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": reply_markup,
                },
            )
        )

    async def send_document(
        self, *, chat_id: str, document: Any, filename: str, caption: str | None = None
    ) -> None:
        self.calls.append(
            (
                "document",
                {
                    "chat_id": chat_id,
                    "document": document,
                    "filename": filename,
                    "caption": caption,
                },
            )
        )
