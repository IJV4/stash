import threading
from collections.abc import Mapping, Sequence

from fakes.chat_model import FakeChatModel

from stash.llm import ChatMessage

GATE_TIMEOUT_SECONDS = 5.0


class GatedChatModel(FakeChatModel):
    def __init__(self, reply: Mapping[str, object] | None = None) -> None:
        super().__init__(reply=reply)
        self.entered = threading.Event()
        self.release = threading.Event()

    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        self.entered.set()
        self.release.wait(GATE_TIMEOUT_SECONDS)
        return super().complete_json(messages, schema, schema_name)
