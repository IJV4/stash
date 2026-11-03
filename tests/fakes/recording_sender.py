from stash.capture import Reply


class RecordingSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Reply]] = []

    async def send(self, chat_id: str, reply: Reply) -> None:
        self.sent.append((chat_id, reply))
