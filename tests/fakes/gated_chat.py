import threading

import httpx
from fakes.fake_providers import OLLAMA_CHAT_PATH, FakeProviders
from threads import OverlapGate


class GatedChat(httpx.BaseTransport):
    def __init__(self, providers: FakeProviders) -> None:
        self._gate = OverlapGate()
        self.release: threading.Event = self._gate.release
        self.entered: threading.Event = self._gate.entered
        self.overlapped: threading.Event = self._gate.overlapped
        self._delegate = providers.client()

    @property
    def max_inside(self) -> int:
        return self._gate.max_inside

    def client(self) -> httpx.Client:
        return httpx.Client(transport=self)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == OLLAMA_CHAT_PATH:
            self._gate.hold()
        return self._delegate.send(request, stream=True)
