import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from stash.enrich.html_meta import HtmlMetaInspector

LONG_CLIENT_TIMEOUT = 120.0
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


@dataclass(slots=True)
class HtmlRig:
    inspector: HtmlMetaInspector
    requests: list[httpx.Request] = field(default_factory=list)

    def requested_urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]


def build_html_rig(
    handler: Handler = not_found, monotonic: Callable[[], float] = time.monotonic
) -> HtmlRig:
    requests: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(recording), timeout=LONG_CLIENT_TIMEOUT)
    return HtmlRig(HtmlMetaInspector(client, monotonic=monotonic), requests)
