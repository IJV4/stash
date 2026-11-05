import json

import httpx
from openai_compat_rig import (
    HELLO,
    OLLAMA,
    OPENROUTER,
    SCHEMA,
    SCHEMA_NAME,
    completion,
    flavours,
    sent_body,
)

from stash.config import ProviderName, ProviderSettings, Thinking
from stash.llm.openai_compat import THINKING_OFF_FIELDS, OpenAICompatibleChat

BASE_KEYS = {"model", "messages", "temperature", "response_format"}
VISION_MODEL = "vision/model"


@flavours
def test_default_thinking_sends_exactly_the_four_base_keys(settings: ProviderSettings) -> None:
    # Execute
    body = sent_body(settings, thinking=Thinking.DEFAULT)

    # Assert
    assert set(body) == BASE_KEYS


@flavours
def test_a_chat_built_without_a_thinking_argument_sends_exactly_the_four_base_keys(
    settings: ProviderSettings,
) -> None:
    # Setup
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completion("{}")

    chat = OpenAICompatibleChat(settings, httpx.Client(transport=httpx.MockTransport(handler)))

    # Execute
    chat.complete_json(HELLO, SCHEMA, SCHEMA_NAME)

    # Assert
    assert set(json.loads(seen[0].content)) == BASE_KEYS


def test_thinking_off_asks_ollama_for_reasoning_effort_none() -> None:
    # Execute
    body = sent_body(OLLAMA, thinking=Thinking.OFF)

    # Assert
    assert body["reasoning_effort"] == "none"


def test_thinking_off_adds_only_reasoning_effort_to_an_ollama_request() -> None:
    # Execute
    body = sent_body(OLLAMA, thinking=Thinking.OFF)

    # Assert
    assert set(body) == BASE_KEYS | {"reasoning_effort"}


def test_thinking_off_asks_openrouter_for_reasoning_effort_none_in_its_reasoning_object() -> None:
    # Execute
    body = sent_body(OPENROUTER, thinking=Thinking.OFF)

    # Assert
    assert body["reasoning"] == {"effort": "none"}


def test_thinking_off_adds_only_reasoning_to_an_openrouter_request() -> None:
    # Execute
    body = sent_body(OPENROUTER, thinking=Thinking.OFF)

    # Assert
    assert set(body) == BASE_KEYS | {"reasoning"}


def test_thinking_off_does_not_send_ollamas_field_to_openrouter() -> None:
    # Execute
    body = sent_body(OPENROUTER, thinking=Thinking.OFF)

    # Assert
    assert "reasoning_effort" not in body


def test_thinking_off_does_not_send_openrouters_field_to_ollama() -> None:
    # Execute
    body = sent_body(OLLAMA, thinking=Thinking.OFF)

    # Assert
    assert "reasoning" not in body


@flavours
def test_thinking_off_leaves_the_base_request_unchanged(settings: ProviderSettings) -> None:
    # Setup
    default = sent_body(settings, thinking=Thinking.DEFAULT)

    # Execute
    off = sent_body(settings, thinking=Thinking.OFF)

    # Assert
    assert {key: off[key] for key in BASE_KEYS} == default


def test_a_model_override_with_thinking_off_still_sends_the_ollama_field() -> None:
    # Execute
    body = sent_body(OLLAMA, model=VISION_MODEL, thinking=Thinking.OFF)

    # Assert
    assert (body["model"], body["reasoning_effort"]) == (VISION_MODEL, "none")


def test_a_model_override_with_thinking_off_still_sends_the_openrouter_field() -> None:
    # Execute
    body = sent_body(OPENROUTER, model=VISION_MODEL, thinking=Thinking.OFF)

    # Assert
    assert (body["model"], body["reasoning"]) == (VISION_MODEL, {"effort": "none"})


def test_every_provider_has_fields_for_turning_thinking_off() -> None:
    # Execute
    providers_with_fields = set(THINKING_OFF_FIELDS)

    # Assert
    assert providers_with_fields == set(ProviderName)
