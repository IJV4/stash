from datetime import UTC, datetime

import pytest
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel

from stash.llm import ChatMessage, LlmUnavailable

SCHEMA: dict[str, object] = {"type": "object"}
HELLO = [ChatMessage.text("user", "hello")]
NOW = datetime(2026, 11, 2, tzinfo=UTC)


def test_a_fake_chat_model_returns_its_reply() -> None:
    # Setup
    model = FakeChatModel(reply={"title": "Ramen"})

    # Execute
    answer = model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {"title": "Ramen"}


def test_a_fake_chat_model_returns_a_copy_of_its_reply() -> None:
    # Setup
    model = FakeChatModel(reply={"title": "Ramen"})
    model.complete_json(HELLO, SCHEMA, "filing")["title"] = "changed"

    # Execute
    answer = model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {"title": "Ramen"}


def test_a_fake_chat_model_without_a_reply_returns_an_empty_object() -> None:
    # Execute
    answer = FakeChatModel().complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {}


def test_a_fake_chat_model_raises_its_error() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("down"))

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match="down"):
        model.complete_json(HELLO, SCHEMA, "filing")


def test_a_fake_chat_model_records_the_messages_it_was_asked() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert model.calls == [HELLO]


def test_a_fake_chat_model_records_the_schema_name_it_was_asked() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert model.schema_names == ["filing"]


def test_a_fake_chat_model_records_a_call_that_raised() -> None:
    # Setup
    model = FakeChatModel(error=LlmUnavailable("down"))

    # Execute
    with pytest.raises(LlmUnavailable):
        model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert model.calls == [HELLO]


def test_a_fake_busy_check_is_free_by_default() -> None:
    # Assert
    assert FakeBusy().is_busy(NOW) is False


def test_a_fake_busy_check_reports_the_flag_set_after_construction() -> None:
    # Setup
    busy = FakeBusy()

    # Execute
    busy.busy = True

    # Assert
    assert busy.is_busy(NOW) is True
