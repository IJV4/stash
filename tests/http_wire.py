import httpx

from stash.http_client import CONNECT_TIMEOUT_SECONDS, DEFAULT_TIMEOUT_SECONDS

DEEPLY_NESTED = "[" * 100_000 + "]" * 100_000
FIVE_SECONDS = {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}


class Wire:
    def __init__(self, outcome: httpx.Response | Exception) -> None:
        self.requests: list[httpx.Request] = []
        self._outcome = outcome

    def client(self) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(self._handle),
            timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    @property
    def request(self) -> httpx.Request:
        return self.requests[0]
