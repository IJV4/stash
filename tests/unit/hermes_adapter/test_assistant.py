import asyncio
import logging
from collections.abc import Mapping

from fakes.recording_sender import RecordingSender
from log_records import recording_logs

from stash.capture import Reply
from stash.hermes_adapter.assistant import GatewayAssistant
from stash.hermes_adapter.events import Chat

CHAT = Chat(chat_id="1001", user_id="42")
TEXT = "what is on my list today?"
APOLOGY = Reply(
    "I couldn't pass that on to the assistant. Send it again starting with ? and I'll hand it over."
)


class ScriptedInject:
    def __init__(self, accepts: bool = True, raises: Exception | None = None) -> None:
        self.calls: list[tuple[str, Mapping[str, str]]] = []
        self._accepts = accepts
        self._raises = raises

    def __call__(self, content: str, *, origin: Mapping[str, str]) -> bool:
        self.calls.append((content, origin))
        if self._raises is not None:
            raise self._raises
        return self._accepts


def test_an_injection_that_raises_apologises_to_the_chat() -> None:
    # Setup
    sender = RecordingSender()
    assistant = GatewayAssistant(ScriptedInject(raises=RuntimeError("boom")), sender)

    # Execute
    asyncio.run(assistant.ask(TEXT, CHAT))

    # Assert
    assert sender.sent == [("1001", APOLOGY)]


def test_an_injection_that_raises_is_logged_as_a_warning_without_the_message_text() -> None:
    # Setup
    assistant = GatewayAssistant(ScriptedInject(raises=RuntimeError("boom")), RecordingSender())

    # Execute
    with recording_logs("stash.hermes_adapter.assistant") as logs:
        asyncio.run(assistant.ask(TEXT, CHAT))

    # Assert
    assert [(level, TEXT in message) for level, message in logs.entries()] == [
        (logging.WARNING, False)
    ]
