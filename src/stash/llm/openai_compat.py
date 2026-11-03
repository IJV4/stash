import json
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

import httpx

from stash.config import ProviderName, ProviderSettings
from stash.llm._auth import bearer_headers
from stash.llm.errors import LlmBadOutput, LlmError, LlmUnavailable
from stash.llm.messages import ChatMessage, ImagePart, Part

ERROR_TEXT_LIMIT = 200
REDACTED = "[redacted]"
RETRYABLE_REJECTIONS = frozenset({402, 408, 429})
SERVER_ERROR_FLOOR = 500
ATTRIBUTION_TITLE = "stash"
UNPARSEABLE_JSON = (ValueError, RecursionError)


def _encode_part(part: Part) -> dict[str, Any]:
    if isinstance(part, ImagePart):
        return {"type": "image_url", "image_url": {"url": part.data_url}}
    return {"type": "text", "text": part.text}


def _encode_message(message: ChatMessage) -> dict[str, Any]:
    return {"role": message.role, "content": [_encode_part(part) for part in message.parts]}


def _is_int_code(code: object) -> TypeGuard[int]:
    return isinstance(code, int) and not isinstance(code, bool)


def _is_retryable(code: object) -> bool:
    if not _is_int_code(code):
        return True
    return code >= SERVER_ERROR_FLOOR or code in RETRYABLE_REJECTIONS


def _message_of(error: object) -> str | None:
    message = error.get("message") if isinstance(error, dict) else None
    return message if isinstance(message, str) else None


class _Failures:
    def __init__(self, settings: ProviderSettings) -> None:
        self._name = settings.name.value
        self._secret = settings.api_key

    def unreachable(self, error: httpx.RequestError) -> LlmUnavailable:
        return LlmUnavailable(f"{self._name} unreachable: {type(error).__name__}")

    def from_status(self, response: httpx.Response) -> LlmError:
        code = response.status_code
        text = self._text_of(response)
        return self._error(code, f"{self._name} answered HTTP {code}: {text}")

    def from_body(self, error: object) -> LlmError:
        code = error.get("code") if isinstance(error, dict) else None
        text = self._clip(_message_of(error) or "")
        label = f"error {code}" if _is_int_code(code) else "an error"
        return self._error(code, f"{self._name} reported {label}: {text}")

    @staticmethod
    def _error(code: object, message: str) -> LlmError:
        return LlmUnavailable(message) if _is_retryable(code) else LlmError(message)

    def _text_of(self, response: httpx.Response) -> str:
        try:
            body = response.json()
        except UNPARSEABLE_JSON:
            return self._clip(response.text)
        message = _message_of(body.get("error") if isinstance(body, dict) else None)
        return self._clip(response.text if message is None else message)

    def _clip(self, text: str) -> str:
        if self._secret:
            text = text.replace(self._secret, REDACTED)
        return text[:ERROR_TEXT_LIMIT]


class OpenAICompatibleChat:
    def __init__(
        self, settings: ProviderSettings, client: httpx.Client, model: str | None = None
    ) -> None:
        if model is not None and not model.strip():
            raise ValueError("model override must not be blank")
        self._client = client
        self._model = settings.model if model is None else model
        self._url = settings.endpoint("chat/completions")
        self._headers = _request_headers(settings)
        self._failures = _Failures(settings)

    def complete_json(
        self,
        messages: Sequence[ChatMessage],
        schema: Mapping[str, object],
        schema_name: str,
    ) -> dict[str, object]:
        payload = self._payload(messages, schema, schema_name)
        return _parse_answer(self._failures, self._send(payload))

    def _payload(
        self, messages: Sequence[ChatMessage], schema: Mapping[str, object], schema_name: str
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [_encode_message(message) for message in messages],
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }

    def _send(self, payload: dict[str, Any]) -> httpx.Response:
        try:
            response = self._client.post(self._url, json=payload, headers=self._headers)
        except httpx.RequestError as error:
            raise self._failures.unreachable(error) from error
        if not response.is_success:
            raise self._failures.from_status(response)
        return response


def _request_headers(settings: ProviderSettings) -> dict[str, str]:
    headers = bearer_headers(settings)
    if settings.name is ProviderName.OPENROUTER:
        headers["X-OpenRouter-Title"] = ATTRIBUTION_TITLE
    return headers


def _parse_answer(failures: _Failures, response: httpx.Response) -> dict[str, object]:
    try:
        body = response.json()
    except UNPARSEABLE_JSON as error:
        raise LlmBadOutput("response was not JSON") from error
    if not isinstance(body, dict):
        raise LlmBadOutput("response was not a JSON object")
    if body.get("error") is not None:
        raise failures.from_body(body["error"])
    return _answer_object(_content_of(body))


def _content_of(body: dict[str, Any]) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LlmBadOutput("response had an unexpected envelope") from error
    if not isinstance(content, str):
        raise LlmBadOutput("response content was not text")
    return content


def _answer_object(content: str) -> dict[str, object]:
    try:
        answer = json.loads(content)
    except UNPARSEABLE_JSON as error:
        raise LlmBadOutput("model output was not valid JSON") from error
    if not isinstance(answer, dict):
        raise LlmBadOutput("model output was not a JSON object")
    return answer
