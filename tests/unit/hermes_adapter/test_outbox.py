import asyncio

import pytest

from stash.capture import Reply
from stash.hermes_adapter.outbox import LateBoundOutbox, OutboxUnavailable

REPLY = Reply("Saved")


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
