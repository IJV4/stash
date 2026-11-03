import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import httpx
import pytest
from builders import an_ollama_settings, chat_body
from fakes.chat_model import FakeChatModel

from stash.llm import ChatMessage, ChatModel, LlmUnavailable
from stash.llm.openai_compat import OpenAICompatibleChat

REPLY = {"a": [1]}
SCHEMA_NAME = "filing"


def a_schema() -> dict[str, object]:
    return {"type": "object", "properties": {"a": {"type": "array"}}}


@dataclass(frozen=True)
class Implementation:
    answering: Callable[[], ChatModel]
    unavailable: Callable[[], ChatModel]


def http_model(handler: Callable[[httpx.Request], httpx.Response]) -> ChatModel:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleChat(an_ollama_settings(), client)


def answering_over_http() -> ChatModel:
    body = chat_body('{"a": [1]}')
    return http_model(lambda request: httpx.Response(200, json=body))


def unavailable_over_http() -> ChatModel:
    return http_model(lambda request: httpx.Response(503, json={"error": "down"}))


IMPLEMENTATIONS = {
    "fake": Implementation(
        answering=lambda: FakeChatModel(reply=REPLY),
        unavailable=lambda: FakeChatModel(error=LlmUnavailable("down")),
    ),
    "openai-compatible": Implementation(
        answering=answering_over_http, unavailable=unavailable_over_http
    ),
}
implementations = pytest.mark.parametrize(
    "implementation", IMPLEMENTATIONS.values(), ids=IMPLEMENTATIONS.keys()
)


def ask(model: ChatModel, messages: list[ChatMessage] | None = None) -> dict[str, object]:
    return model.complete_json(
        messages or [ChatMessage.text("user", "hi")], a_schema(), SCHEMA_NAME
    )


@implementations
def test_a_top_level_change_to_one_answer_does_not_leak_into_the_next(
    implementation: Implementation,
) -> None:
    # Setup
    model = implementation.answering()
    ask(model)["extra"] = True

    # Execute
    second = ask(model)

    # Assert
    assert "extra" not in second


@implementations
def test_a_nested_change_to_one_answer_does_not_leak_into_the_next(
    implementation: Implementation,
) -> None:
    # Setup
    model = implementation.answering()
    cast(list[int], ask(model)["a"]).append(2)

    # Execute
    second = ask(model)

    # Assert
    assert second == {"a": [1]}


@implementations
def test_the_messages_it_is_given_are_left_unchanged(implementation: Implementation) -> None:
    # Setup
    messages = [ChatMessage.text("system", "be brief"), ChatMessage.text("user", "hi")]
    snapshot = copy.deepcopy(messages)

    # Execute
    ask(implementation.answering(), messages)

    # Assert
    assert messages == snapshot


@implementations
def test_the_schema_it_is_given_is_left_unchanged(implementation: Implementation) -> None:
    # Setup
    schema = a_schema()

    # Execute
    implementation.answering().complete_json([ChatMessage.text("user", "hi")], schema, SCHEMA_NAME)

    # Assert
    assert schema == a_schema()


@implementations
def test_an_unavailable_backend_is_signalled_with_llm_unavailable(
    implementation: Implementation,
) -> None:
    # Setup
    model = implementation.unavailable()

    # Execute / Assert
    with pytest.raises(LlmUnavailable):
        ask(model)
