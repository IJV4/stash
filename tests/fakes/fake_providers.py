import json
from collections.abc import Mapping
from typing import Any

import httpx

OLLAMA_HOST = "localhost"
OPENROUTER_HOST = "openrouter.ai"
LIBRARY_HOST = "127.0.0.1"
OLLAMA_CHAT_PATH = "/v1/chat/completions"
UNKNOWN = httpx.Response(404, json={"error": "unknown endpoint"})
HTML = {"content-type": "text/html; charset=utf-8"}
THINKING_FIELDS = frozenset({"reasoning_effort", "reasoning"})

FILING_ANSWER: Mapping[str, object] = {
    "route": "capture",
    "item_type": "place",
    "title": "Ichiran ramen",
    "stage": "want_to",
    "details": {},
    "tags": [],
    "people": [],
    "date": None,
}


def thinking_fields(body: Mapping[str, Any]) -> dict[str, Any]:
    return {key: body[key] for key in THINKING_FIELDS & body.keys()}


def _chat_reply(answer: Mapping[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(answer)}}]})


class FakeProviders:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.ollama_models: list[str] = ["local-model"]
        self.ollama_reachable = True
        self.openrouter_key_valid = True
        self.openrouter_models: list[str] = ["cloud/model"]
        self.answer: Mapping[str, object] = FILING_ANSWER
        self.pages: dict[str, str] = {}
        self.library_listening = True

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle))

    def sent_to(self, path: str) -> list[httpx.Request]:
        return [request for request in self.requests if request.url.path == path]

    def chat_bodies(self, path: str) -> list[dict[str, Any]]:
        return [json.loads(request.content) for request in self.sent_to(path)]

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) in self.pages:
            return httpx.Response(200, headers=HTML, content=self.pages[str(request.url)].encode())
        if request.url.host == OLLAMA_HOST:
            return self._ollama(request)
        if request.url.host == OPENROUTER_HOST:
            return self._openrouter(request)
        if request.url.host == LIBRARY_HOST:
            return self._library(request)
        return UNKNOWN

    def _ollama(self, request: httpx.Request) -> httpx.Response:
        if not self.ollama_reachable:
            raise httpx.ConnectError("connection refused", request=request)
        match request.url.path:
            case "/api/tags":
                return httpx.Response(
                    200, json={"models": [{"name": name} for name in self.ollama_models]}
                )
            case "/api/ps":
                return httpx.Response(200, json={"models": []})
            case "/api/generate":
                return httpx.Response(200, json={"done": True})
            case "/v1/chat/completions":
                return _chat_reply(self.answer)
        return UNKNOWN

    def _library(self, request: httpx.Request) -> httpx.Response:
        if not self.library_listening:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, text="ok") if request.url.path == "/healthz" else UNKNOWN

    def _openrouter(self, request: httpx.Request) -> httpx.Response:
        if not self.openrouter_key_valid:
            return httpx.Response(401, json={"error": {"message": "invalid key"}})
        match request.url.path:
            case "/api/v1/key":
                return httpx.Response(200, json={"data": {"limit_remaining": 10}})
            case "/api/v1/models":
                return httpx.Response(
                    200, json={"data": [{"id": name} for name in self.openrouter_models]}
                )
            case "/api/v1/chat/completions":
                return _chat_reply(self.answer)
        return UNKNOWN
