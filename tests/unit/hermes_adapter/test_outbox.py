import asyncio
from dataclasses import dataclass, field

import pytest

from stash.capture import Reply
from stash.hermes_adapter.outbox import LateBoundOutbox, OutboxUnavailable

REPLY = Reply("Saved")
OTHER_REPLY = Reply("Saved again")


@dataclass
class ScriptedOutbox:
    calls: list[tuple[object, ...]] = field(default_factory=list)

    async def send(self, chat_id: str, reply: Reply) -> None:
        self.calls.append(("send", chat_id, None, reply))

    async def edit(self, chat_id: str, message_id: str, reply: Reply) -> None:
        self.calls.append(("edit", chat_id, message_id, reply))

    async def send_file(self, chat_id: str, filename: str, data: bytes, caption: str) -> None:
        self.calls.append(("file", chat_id, filename, data, caption))


def test_sending_before_an_outbox_is_bound_raises_outbox_unavailable() -> None:
    # Setup
    outbox = LateBoundOutbox()

    # Execute
    with pytest.raises(OutboxUnavailable) as refusal:
        asyncio.run(outbox.send("1001", REPLY))

    # Assert
    assert refusal.type is OutboxUnavailable


def test_editing_before_an_outbox_is_bound_raises_outbox_unavailable() -> None:
    # Setup
    outbox = LateBoundOutbox()

    # Execute
    with pytest.raises(OutboxUnavailable) as refusal:
        asyncio.run(outbox.edit("1001", "55", REPLY))

    # Assert
    assert refusal.type is OutboxUnavailable


def test_sending_after_binding_goes_to_the_bound_outbox() -> None:
    # Setup
    bound = ScriptedOutbox()
    outbox = LateBoundOutbox()
    outbox.bind(bound)

    # Execute
    asyncio.run(outbox.send("1001", REPLY))

    # Assert
    assert bound.calls == [("send", "1001", None, REPLY)]


def test_editing_after_binding_goes_to_the_bound_outbox() -> None:
    # Setup
    bound = ScriptedOutbox()
    outbox = LateBoundOutbox()
    outbox.bind(bound)

    # Execute
    asyncio.run(outbox.edit("1001", "55", REPLY))

    # Assert
    assert bound.calls == [("edit", "1001", "55", REPLY)]


def test_rebinding_replaces_the_outbox_that_receives_replies() -> None:
    # Setup
    first, second = ScriptedOutbox(), ScriptedOutbox()
    outbox = LateBoundOutbox()
    outbox.bind(first)
    outbox.bind(second)

    # Execute
    asyncio.run(outbox.send("1001", OTHER_REPLY))

    # Assert
    assert (first.calls, second.calls) == ([], [("send", "1001", None, OTHER_REPLY)])


def test_sending_a_file_before_an_outbox_is_bound_raises_outbox_unavailable() -> None:
    # Setup
    outbox = LateBoundOutbox()

    # Execute
    with pytest.raises(OutboxUnavailable) as refusal:
        asyncio.run(outbox.send_file("1001", "library.html", b"<p>", "caption"))

    # Assert
    assert refusal.type is OutboxUnavailable


def test_sending_a_file_after_binding_goes_to_the_bound_outbox() -> None:
    # Setup
    bound = ScriptedOutbox()
    outbox = LateBoundOutbox()
    outbox.bind(bound)

    # Execute
    asyncio.run(outbox.send_file("1001", "library.html", b"<p>", "caption"))

    # Assert
    assert bound.calls == [("file", "1001", "library.html", b"<p>", "caption")]
