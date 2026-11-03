from dataclasses import dataclass

from stash.capture import Reply


@dataclass(frozen=True, slots=True)
class SentReply:
    chat_id: str
    reply: Reply


@dataclass(frozen=True, slots=True)
class EditedReply:
    chat_id: str
    message_id: str
    reply: Reply


class RecordingOutbox:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.sent: list[SentReply] = []
        self.edited: list[EditedReply] = []

    async def send(self, chat_id: str, reply: Reply) -> None:
        self._fail_if_told_to()
        self.sent.append(SentReply(chat_id, reply))

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        self._fail_if_told_to()
        self.edited.append(EditedReply(chat_id, message_id, reply))

    def sent_texts(self) -> list[str]:
        return [sent.reply.text for sent in self.sent]

    def _fail_if_told_to(self) -> None:
        if self.failure is not None:
            raise self.failure
