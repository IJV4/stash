from datetime import UTC, datetime, timedelta

import pytest
from fakes.busy import BusyUntil, FakeBusy
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


def test_a_fake_chat_model_works_again_once_its_error_is_cleared() -> None:
    # Setup
    model = FakeChatModel(reply={"title": "Ramen"}, error=LlmUnavailable("down"))
    model.error = None

    # Execute
    answer = model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {"title": "Ramen"}


def test_a_fake_chat_model_fails_once_an_error_is_set() -> None:
    # Setup
    model = FakeChatModel()
    model.error = LlmUnavailable("down")

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match="down"):
        model.complete_json(HELLO, SCHEMA, "filing")


def test_a_fake_chat_model_returns_the_reply_set_after_construction() -> None:
    # Setup
    model = FakeChatModel(reply={"title": "Ramen"})
    model.reply = {"title": "Sushi"}

    # Execute
    answer = model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {"title": "Sushi"}


def test_a_fake_chat_model_records_the_schema_it_was_asked() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert model.schemas == [SCHEMA]


def test_a_fake_chat_model_returns_a_deep_copy_of_its_reply() -> None:
    # Setup
    model = FakeChatModel(reply={"tags": ["ramen"]})
    first = model.complete_json(HELLO, SCHEMA, "filing")
    first["tags"].append("changed")  # type: ignore[attr-defined]

    # Execute
    answer = model.complete_json(HELLO, SCHEMA, "filing")

    # Assert
    assert answer == {"tags": ["ramen"]}


def test_a_busy_until_check_is_busy_before_its_deadline() -> None:
    # Assert
    assert BusyUntil(NOW + timedelta(seconds=1)).is_busy(NOW) is True


def test_a_busy_until_check_is_free_at_its_deadline() -> None:
    # Assert
    assert BusyUntil(NOW).is_busy(NOW) is False
