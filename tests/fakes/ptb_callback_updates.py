from datetime import UTC, datetime
from typing import Any

from telegram import Bot, CallbackQuery, Chat, Message, Update, User
from telegram.request import BaseRequest

FAKE_TOKEN = "123456:fake-token-for-offline-tests"
SENT_AT = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


class OfflineRequest(BaseRequest):
    @property
    def read_timeout(self) -> float | None:
        return None

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def do_request(self, *args: Any, **kwargs: Any) -> tuple[int, bytes]:
        raise ConnectionError("offline test request must never be used")


class AnsweringBot(Bot):
    def __init__(self, log: list[str], failure: Exception | None = None) -> None:
        super().__init__(FAKE_TOKEN, request=OfflineRequest(), get_updates_request=OfflineRequest())
        self._log = log
        self._failure = failure

    async def answer_callback_query(
        self, callback_query_id: str, *args: Any, **kwargs: Any
    ) -> bool:
        self._log.append("answer")
        if self._failure is not None:
            raise self._failure
        return True


def callback_update(
    bot: Bot,
    data: str | None = "stash:t:abc",
    chat_id: int = 1001,
    user_id: int = 42,
    message_id: int = 55,
    with_message: bool = True,
) -> Update:
    sender = User(id=user_id, first_name="Owner", is_bot=False)
    message = (
        Message(
            message_id=message_id,
            date=SENT_AT,
            chat=Chat(id=chat_id, type=Chat.PRIVATE),
        )
        if with_message
        else None
    )
    query = CallbackQuery(
        id="query-1", from_user=sender, chat_instance="instance", data=data, message=message
    )
    query.set_bot(bot)
    return Update(update_id=1, callback_query=query)
