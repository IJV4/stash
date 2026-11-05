import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from builders import an_ollama_settings, an_openrouter_settings, chat_body

from stash.config import ProviderSettings, Thinking
from stash.llm import ChatMessage, LlmError
from stash.llm.openai_compat import OpenAICompatibleChat

SCHEMA: dict[str, object] = {"type": "object", "properties": {"a": {"type": "integer"}}}
SCHEMA_NAME = "filing"
HELLO = [ChatMessage.text("user", "hello")]
OLLAMA = an_ollama_settings()
OPENROUTER = an_openrouter_settings()
FLAVOURS = {"ollama": OLLAMA, "openrouter": OPENROUTER}
flavours = pytest.mark.parametrize("settings", FLAVOURS.values(), ids=FLAVOURS.keys())

Handler = Callable[[httpx.Request], httpx.Response]


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json=chat_body(content))


def answering(response: httpx.Response) -> Handler:
    return lambda request: response


def raising(error: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


def chat_over(
    settings: ProviderSettings,
    handler: Handler,
    model: str | None = None,
    thinking: Thinking = Thinking.DEFAULT,
) -> OpenAICompatibleChat:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatibleChat(settings, client, model, thinking)


def ask(
    settings: ProviderSettings,
    handler: Handler,
    messages: list[ChatMessage] | None = None,
    model: str | None = None,
    thinking: Thinking = Thinking.DEFAULT,
) -> dict[str, object]:
    chat = chat_over(settings, handler, model, thinking)
    return chat.complete_json(messages or HELLO, SCHEMA, SCHEMA_NAME)


def sent_request(
    settings: ProviderSettings,
    messages: list[ChatMessage] | None = None,
    model: str | None = None,
    thinking: Thinking = Thinking.DEFAULT,
) -> httpx.Request:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completion("{}")

    ask(settings, handler, messages, model, thinking)
    return seen[0]


def sent_body(
    settings: ProviderSettings,
    messages: list[ChatMessage] | None = None,
    model: str | None = None,
    thinking: Thinking = Thinking.DEFAULT,
) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(sent_request(settings, messages, model, thinking).content)
    return body


def failure_of(settings: ProviderSettings, handler: Handler) -> LlmError:
    with pytest.raises(LlmError) as raised:
        ask(settings, handler)
    return raised.value
