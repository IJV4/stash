from stash.hermes_adapter.events import Chat


class RecordingAssistant:
    def __init__(self) -> None:
        self.asked: list[tuple[str, Chat]] = []

    async def ask(self, text: str, chat: Chat) -> None:
        self.asked.append((text, chat))
