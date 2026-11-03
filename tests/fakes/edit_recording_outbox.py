from stash.capture import Reply


class EditFailed(Exception):
    pass


class EditRecordingOutbox:
    def __init__(self, edit_failure: Exception | None = None) -> None:
        self._edit_failure = edit_failure
        self.sent: list[tuple[str, Reply]] = []
        self.edits: list[tuple[str, str, Reply]] = []

    async def send(self, chat_id: str, reply: Reply) -> None:
        self.sent.append((chat_id, reply))

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        if self._edit_failure is not None:
            raise self._edit_failure
        self.edits.append((chat_id, message_id, reply))
