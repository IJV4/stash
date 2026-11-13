import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import httpx

from stash.enrich.html_meta import HtmlMetaInspector

LONG_CLIENT_TIMEOUT = 120.0
PUBLIC_ADDRESS = "93.184.216.34"
Handler = Callable[[httpx.Request], httpx.Response]


def html_page(body: str, content_type: str = "text/html; charset=utf-8") -> httpx.Response:
    return httpx.Response(200, headers={"content-type": content_type}, content=body.encode())


def not_found(request: httpx.Request) -> httpx.Response:
    return httpx.Response(404)


def redirect_to(location: str) -> httpx.Response:
    return httpx.Response(302, headers=[(b"location", location.encode())])


def page_with_title(title: str) -> httpx.Response:
    return html_page(f"<html><head><title>{title}</title></head></html>")


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class FakeResolver:
    def __init__(
        self, answers: Mapping[str, Sequence[str]] | None = None, error: OSError | None = None
    ) -> None:
        self.calls: list[tuple[str, int]] = []
        self._answers = answers or {}
        self._error = error

    def __call__(self, host: str, port: int) -> Sequence[str]:
        self.calls.append((host, port))
        if self._error is not None:
            raise self._error
        return self._answers.get(host, (PUBLIC_ADDRESS,))


def requested_url(request: httpx.Request) -> str:
    return str(request.url.copy_with(netloc=request.headers["host"].encode()))


@dataclass(slots=True)
class HtmlRig:
    inspector: HtmlMetaInspector
    requests: list[httpx.Request] = field(default_factory=list)

    def requested_urls(self) -> list[str]:
        return [requested_url(request) for request in self.requests]


def build_html_rig(
    handler: Handler = not_found,
    monotonic: Callable[[], float] = time.monotonic,
    resolve: Callable[[str, int], Sequence[str]] | None = None,
) -> HtmlRig:
    requests: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(recording), timeout=LONG_CLIENT_TIMEOUT)
    inspector = HtmlMetaInspector(client, resolve=resolve or FakeResolver(), monotonic=monotonic)
    return HtmlRig(inspector, requests)
