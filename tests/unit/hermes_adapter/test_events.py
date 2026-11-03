import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from builders import BASE
from log_records import recording_logs

from stash.capture import IncomingMessage
from stash.domain import SourceRef
from stash.hermes_adapter.events import (
    Chat,
    EventTranslator,
    Inbound,
    Passthrough,
    Verdict,
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


def test_allow_is_the_hook_result_that_lets_hermes_carry_on() -> None:
    # Setup
    verdict = Verdict.ALLOW

    # Execute
    result = verdict.hook_result()

    # Assert
    assert result == {"action": "allow"}


def test_skip_is_the_hook_result_that_stops_hermes() -> None:
    # Setup
    verdict = Verdict.SKIP

    # Execute
    result = verdict.hook_result()

    # Assert
    assert result == {"action": "skip"}


def test_an_owners_plain_text_becomes_an_inbound_message() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent())

    # Assert
    assert outcome == Inbound(
        Chat(CHAT, OWNER),
        IncomingMessage(SourceRef(CHAT, "m-1"), "buy oat milk", (), BASE),
    )


def test_the_received_time_is_read_from_the_clock() -> None:
    # Setup
    later = datetime(2027, 1, 2, 3, 4, tzinfo=UTC)
    translator = a_translator(clock=lambda: later)

    # Execute
    outcome = translator.read(FakeEvent())

    # Assert
    assert isinstance(outcome, Inbound) and outcome.message.received_at == later


def test_media_paths_travel_with_the_message() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(media_urls=["/tmp/a.jpg", "/tmp/b.jpg"])

    # Execute
    outcome = translator.read(event)

    # Assert
    assert isinstance(outcome, Inbound) and outcome.message.media_paths == (
        "/tmp/a.jpg",
        "/tmp/b.jpg",
    )


def test_a_message_with_only_media_becomes_an_inbound_with_empty_text() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(text=None, media_urls=["/tmp/a.jpg"])

    # Execute
    outcome = translator.read(event)

    # Assert
    assert isinstance(outcome, Inbound) and (outcome.message.text, outcome.message.media_paths) == (
        "",
        ("/tmp/a.jpg",),
    )


def test_a_missing_media_list_means_no_media() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(media_urls=None)

    # Execute
    outcome = translator.read(event)

    # Assert
    assert isinstance(outcome, Inbound) and outcome.message.media_paths == ()


def test_a_missing_message_id_is_replaced_by_a_generated_one() -> None:
    # Setup
    translator = a_translator(new_id=lambda: "generated-7")

    # Execute
    outcome = translator.read(FakeEvent(message_id=None))

    # Assert
    assert isinstance(outcome, Inbound) and outcome.message.source == SourceRef(CHAT, "generated-7")


def test_a_present_message_id_does_not_draw_a_generated_one() -> None:
    # Setup
    drawn: list[str] = []

    def new_id() -> str:
        drawn.append("drawn")
        return "generated"

    translator = a_translator(new_id=new_id)

    # Execute
    translator.read(FakeEvent(message_id="m-9"))

    # Assert
    assert drawn == []


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


def test_someone_who_is_not_an_owner_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator(owners="7")

    # Execute
    outcome = translator.read(FakeEvent())

    # Assert
    assert outcome == Passthrough()


def test_nobody_is_an_owner_when_no_owners_are_configured() -> None:
    # Setup
    translator = a_translator(owners="")

    # Execute
    outcome = translator.read(FakeEvent())

    # Assert
    assert outcome == Passthrough()


def test_an_event_without_a_user_id_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(source=FakeSource(user_id=None))

    # Execute
    outcome = translator.read(event)

    # Assert
    assert outcome == Passthrough()


def test_an_event_with_a_blank_user_id_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(source=FakeSource(user_id="  "))

    # Execute
    outcome = translator.read(event)

    # Assert
    assert outcome == Passthrough()


def test_a_slash_command_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent(text="/list"))

    # Assert
    assert outcome == Passthrough()


def test_a_slash_command_after_leading_spaces_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent(text="  /gpu on"))

    # Assert
    assert outcome == Passthrough()


def test_a_slash_command_with_media_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(text="/retry", media_urls=["/tmp/a.jpg"])

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


def test_a_synthetic_event_from_an_owner_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()

    # Execute
    outcome = translator.read(FakeEvent(internal=True))

    # Assert
    assert outcome == Passthrough()


def test_an_owner_event_with_a_blank_chat_id_is_left_to_hermes() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(source=FakeSource(chat_id="  ", user_id=OWNER))

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


def test_accepted_media_paths_log_nothing() -> None:
    # Setup
    translator = a_translator()
    event = FakeEvent(media_urls=["/tmp/a.jpg"])

    # Execute
    with recording_logs(LOGGER) as logs:
        translator.read(event)

    # Assert
    assert logs.entries() == []
