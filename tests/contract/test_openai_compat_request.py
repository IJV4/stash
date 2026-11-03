import json

import httpx
import pytest
from builders import API_KEY, an_ollama_settings, an_openrouter_settings
from openai_compat_rig import (
    HELLO,
    OLLAMA,
    OPENROUTER,
    SCHEMA,
    SCHEMA_NAME,
    answering,
    chat_over,
    completion,
    flavours,
    sent_body,
    sent_request,
)

from stash.config import ProviderSettings
from stash.llm import ChatMessage, ImagePart, TextPart

DATA_URL = "data:image/png;base64,AAAA"


@flavours
def test_the_request_is_posted_to_chat_completions_under_the_base_url(
    settings: ProviderSettings,
) -> None:
    # Execute
    request = sent_request(settings)

    # Assert
    assert (request.method, str(request.url)) == (
        "POST",
        f"{settings.base_url}/chat/completions",
    )


def test_a_trailing_slash_on_the_base_url_does_not_double_the_slash() -> None:
    # Setup
    settings = an_ollama_settings(base_url="http://localhost:11434/v1/")

    # Execute
    request = sent_request(settings)

    # Assert
    assert str(request.url) == "http://localhost:11434/v1/chat/completions"


@flavours
def test_the_request_body_names_the_configured_model(settings: ProviderSettings) -> None:
    # Execute
    body = sent_body(settings)

    # Assert
    assert body["model"] == settings.model


@flavours
def test_the_model_override_argument_is_sent_instead_of_the_configured_model(
    settings: ProviderSettings,
) -> None:
    # Execute
    body = sent_body(settings, model="vision-model")

    # Assert
    assert body["model"] == "vision-model"


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_model_override_raises_value_error(blank: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="model"):
        chat_over(OLLAMA, answering(completion("{}")), model=blank)


@flavours
def test_the_request_asks_for_temperature_zero(settings: ProviderSettings) -> None:
    # Execute
    body = sent_body(settings)

    # Assert
    assert body["temperature"] == 0


@flavours
def test_the_request_forces_a_json_schema_response_format(settings: ProviderSettings) -> None:
    # Execute
    body = sent_body(settings)

    # Assert
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": SCHEMA_NAME, "strict": True, "schema": SCHEMA},
    }


@flavours
def test_the_response_format_schema_name_is_the_one_given(settings: ProviderSettings) -> None:
    # Setup
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completion("{}")

    # Execute
    chat_over(settings, handler).complete_json(HELLO, SCHEMA, "suggestions")

    # Assert
    assert json.loads(seen[0].content)["response_format"]["json_schema"]["name"] == "suggestions"


@flavours
def test_a_text_part_is_encoded_as_a_text_content_part(settings: ProviderSettings) -> None:
    # Execute
    body = sent_body(settings, [ChatMessage("user", (TextPart("what is this"),))])

    # Assert
    assert body["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "what is this"}]}
    ]


@flavours
def test_an_image_part_is_encoded_as_an_image_url_content_part(
    settings: ProviderSettings,
) -> None:
    # Execute
    body = sent_body(settings, [ChatMessage("user", (ImagePart(DATA_URL),))])

    # Assert
    assert body["messages"] == [
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": DATA_URL}}]}
    ]


@flavours
def test_messages_are_sent_in_order_with_their_roles(settings: ProviderSettings) -> None:
    # Setup
    messages = [ChatMessage.text("system", "rules"), ChatMessage.text("user", "hi")]

    # Execute
    body = sent_body(settings, messages)

    # Assert
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_the_openrouter_flavour_sends_the_api_key_as_a_bearer_token() -> None:
    # Execute
    request = sent_request(OPENROUTER)

    # Assert
    assert request.headers["authorization"] == f"Bearer {API_KEY}"


def test_the_openrouter_flavour_sends_the_attribution_title() -> None:
    # Execute
    request = sent_request(OPENROUTER)

    # Assert
    assert request.headers["x-openrouter-title"] == "stash"


def test_the_ollama_flavour_sends_no_authorization_header() -> None:
    # Execute
    request = sent_request(OLLAMA)

    # Assert
    assert "authorization" not in request.headers


def test_the_ollama_flavour_sends_no_attribution_title() -> None:
    # Execute
    request = sent_request(OLLAMA)

    # Assert
    assert "x-openrouter-title" not in request.headers


def test_an_api_key_on_a_non_openrouter_provider_is_still_sent_as_a_bearer_token() -> None:
    # Setup
    keyed_ollama = an_ollama_settings(api_key="k")

    # Execute
    request = sent_request(keyed_ollama)

    # Assert
    assert request.headers["authorization"] == "Bearer k"


def test_an_openrouter_provider_without_a_key_sends_no_authorization_header() -> None:
    # Setup
    keyless = an_openrouter_settings(api_key=None)

    # Execute
    request = sent_request(keyless)

    # Assert
    assert "authorization" not in request.headers
