import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

import pytest
from builders import BASE
from log_records import recording_logs

from stash.domain import SourceRef
from stash.domain.capture import AGENT_CHAT_ID
from stash.hermes_adapter.events import (
    Chat,
    EventTranslator,
    Inbound,
    Passthrough,
)
from stash.hermes_adapter.owners import Owners

OWNER = "42"
CHAT = "1001"
LOGGER = "stash.hermes_adapter.events"


@dataclass(frozen=True)
class FakeSource:
    chat_id: str = CHAT
    user_id: str | None = OWNER


@dataclass(frozen=True)
class FakeEvent:
    text: str | None = "buy oat milk"
    source: FakeSource = FakeSource()
    message_id: str | None = "m-1"
    media_urls: Sequence[str] | None = None
    internal: bool = False


def counting_ids() -> Callable[[], str]:
    issued: list[str] = []

    def new_id() -> str:
        issued.append(f"generated-{len(issued) + 1}")
        return issued[-1]

    return new_id


def a_translator(
    owners: str = OWNER,
    clock: Callable[[], datetime] = lambda: BASE,
    new_id: Callable[[], str] | None = None,
) -> EventTranslator:
    return EventTranslator(Owners.parse(owners), clock, new_id or counting_ids())


def test_a_chat_with_a_blank_chat_id_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="chat_id"):
        Chat(chat_id="  ", user_id=OWNER)


def test_a_chat_with_a_blank_user_id_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="user_id"):
        Chat(chat_id=CHAT, user_id="")


def test_a_missing_message_id_is_replaced_by_a_generated_one() -> None:
    # Setup
    translator = a_translator(new_id=lambda: "generated-7")

    # Execute
    outcome = translator.read(FakeEvent(message_id=None))

    # Assert
    assert isinstance(outcome, Inbound) and outcome.message.source == SourceRef(CHAT, "generated-7")


def test_media_that_the_domain_refuses_is_dropped_but_the_text_is_kept() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(media_urls=["/tmp/../etc/passwd"])

    # Execute
    outcome = translator.read(event)

    # Assert
    assert isinstance(outcome, Inbound) and (outcome.message.text, outcome.message.media_paths) == (
        "buy oat milk",
        (),
    )


def test_a_message_whose_only_media_is_refused_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(text=None, media_urls=["/tmp/../etc/passwd"])

    # Execute
    outcome = translator.read(event)

    # Assert
    assert outcome == Passthrough()


def test_an_event_without_text_or_media_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent(text=None, media_urls=None))

    # Assert
    assert outcome == Passthrough()


def test_an_event_with_blank_text_and_an_empty_media_list_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent(text="   ", media_urls=[]))

    # Assert
    assert outcome == Passthrough()


def test_an_owner_event_from_the_reserved_agent_chat_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(source=FakeSource(chat_id=AGENT_CHAT_ID, user_id=OWNER))

    # Execute
    outcome = translator.read(event)

    # Assert
    assert outcome == Passthrough()


def test_a_stranger_event_with_a_blank_chat_id_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator(owners="7")
    event = FakeEvent(source=FakeSource(chat_id="", user_id=OWNER))

    # Execute
    outcome = translator.read(event)

    # Assert
    assert outcome == Passthrough()


def test_refused_media_paths_are_reported_by_count_in_one_warning() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(media_urls=["/tmp/../etc/passwd", "/tmp/../etc/shadow"])

    # Execute
    with recording_logs(LOGGER) as logs:
        translator.read(event)

    # Assert
    assert logs.entries() == [(logging.WARNING, "dropped 2 media paths that stash refuses")]
