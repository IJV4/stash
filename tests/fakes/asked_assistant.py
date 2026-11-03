from stash.hermes_adapter.events import Chat


class AskedAssistant:
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure
        self.asked: list[tuple[str, Chat]] = []

    async def ask(self, text: str, chat: Chat) -> None:
        self.asked.append((text, chat))
        if self._failure is not None:
            raise self._failure
