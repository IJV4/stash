from collections.abc import Callable, Mapping

import httpx
import pytest
from fakes.link_inspector import FakeLinkInspector
from html_rig import build_html_rig, html_page, not_found

from stash.enrich.html_meta import HtmlMetaInspector
from stash.enrich.links import FallbackInspector, LinkInfo, LinkInspector
from stash.enrich.ytdlp import YtDlpInspector

URL = "https://example.com/ramen"
Builder = Callable[[], LinkInspector]


def _exploding_extract(url: str) -> Mapping[str, object]:
    raise RuntimeError("extractor blew up")


def _titled_extract(url: str) -> Mapping[str, object]:
    return {"title": "Ramen"}


def _titled_page(request: httpx.Request) -> httpx.Response:
    return html_page("<title>Ramen</title>")


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("no route")


def _html(handler: Callable[[httpx.Request], httpx.Response]) -> HtmlMetaInspector:
    return build_html_rig(handler).inspector


UNABLE: dict[str, Builder] = {
    "fake": FakeLinkInspector,
    "ytdlp-raising": lambda: YtDlpInspector(_exploding_extract),
    "html-404": lambda: _html(not_found),
    "html-unreachable": lambda: _html(_unreachable),
    "fallback": lambda: FallbackInspector(YtDlpInspector(_exploding_extract), _html(not_found)),
}
unable = pytest.mark.parametrize("build", UNABLE.values(), ids=UNABLE.keys())


@unable
def test_an_inspector_that_cannot_describe_a_link_returns_unknown_instead_of_raising(
    build: Builder,
) -> None:
    # Execute
    info = build().inspect(URL)

    # Assert
    assert info == LinkInfo.unknown(URL)
