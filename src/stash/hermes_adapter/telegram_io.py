import logging
from typing import TYPE_CHECKING, Any, Protocol

from stash.capture import Reply
from stash.hermes_adapter.callbacks import CallbackPress, PressHandler
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.outbox import LateBoundOutbox

if TYPE_CHECKING:
    from telegram import CallbackQuery, InlineKeyboardMarkup, Update

logger = logging.getLogger(__name__)

STASH_BUTTON_PATTERN = r"^stash:"


class TelegramBot(Protocol):
    async def send_message(
        self, *, chat_id: str, text: str, reply_markup: Any = None
    ) -> object: ...

    async def edit_message_text(
        self, *, text: str, chat_id: str, message_id: int, reply_markup: Any = None
    ) -> object: ...


class TelegramApplication(Protocol):
    @property
    def bot(self) -> TelegramBot: ...

    def add_handler(self, handler: Any) -> None: ...


def to_keyboard(reply: Reply) -> "InlineKeyboardMarkup | None":
    if not reply.buttons:
        return None
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(button.label, callback_data=button.data) for button in row]
            for row in reply.buttons
        ]
    )


class TelegramOutbox:
    def __init__(self, bot: TelegramBot) -> None:
        self._bot = bot

    async def send(self, chat_id: str, reply: Reply) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text=reply.text, reply_markup=to_keyboard(reply)
        )

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        await self._bot.edit_message_text(
            text=reply.text,
            chat_id=chat_id,
            message_id=int(message_id),
            reply_markup=to_keyboard(reply),
        )


class TelegramAttachment:
    def __init__(self, outbox: LateBoundOutbox, on_press: PressHandler) -> None:
        self._outbox = outbox
        self._on_press = on_press
        self._attached_to: TelegramApplication | None = None

    def attach(self, application: TelegramApplication) -> None:
        from telegram.ext import CallbackQueryHandler

        self._outbox.bind(TelegramOutbox(application.bot))
        if application is self._attached_to:
            return
        application.add_handler(CallbackQueryHandler(self._on_update, pattern=STASH_BUTTON_PATTERN))
        self._attached_to = application

    async def _acknowledge(self, query: "CallbackQuery") -> None:
        try:
            await query.answer()
        except Exception as failure:
            chat_id = "unknown" if query.message is None else query.message.chat.id
            logger.warning(
                "could not acknowledge a button press in chat %s: %s",
                chat_id,
                type(failure).__name__,
            )

    async def _on_update(self, update: "Update", context: object) -> None:
        query = update.callback_query
        if query is None:
            return
        await self._acknowledge(query)
        if query.message is None or query.data is None:
            return
        chat = Chat(str(query.message.chat.id), str(query.from_user.id))
        press = CallbackPress(chat, str(query.message.message_id), query.data)
        try:
            await self._on_press(press)
        except Exception:
            logger.exception("callback press failed for chat %s", chat.chat_id)
