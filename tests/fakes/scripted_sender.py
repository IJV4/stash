from collections.abc import Callable

from stash.capture import Reply


class SendFailed(Exception):
    pass


class ScriptedSender:
    def __init__(self, failures: int = 0, on_send: Callable[[], None] | None = None) -> None:
        self._failures = failures
        self._on_send = on_send
        self.attempts = 0
        self.sent: list[tuple[str, Reply]] = []

    async def send(self, chat_id: str, reply: Reply) -> None:
        self.attempts += 1
        if self._on_send is not None:
            hook, self._on_send = self._on_send, None
            hook()
        if self._failures > 0:
            self._failures -= 1
            raise SendFailed("telegram is down")
        self.sent.append((chat_id, reply))
