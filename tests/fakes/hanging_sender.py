import asyncio

from stash.capture import Reply


class HangingSender:
    def __init__(self) -> None:
        self.attempts = 0
        self.cancelled = 0

    async def send(self, chat_id: str, reply: Reply) -> None:
        self.attempts += 1
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
