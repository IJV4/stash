from collections.abc import Mapping

import httpx
from fakes.hung_link_inspector import HungLinkInspector
from html_rig import html_page

from stash.app.inspection import INSPECTION_DEADLINE_SECONDS, build_inspector
from stash.enrich.links import LinkInfo

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
PAGE = "<html><head><title>Ramen Tokyo</title></head></html>"
SHORT_DEADLINE_SECONDS = 0.005


def a_page_reader(requests: list[httpx.Request]) -> httpx.Client:
    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return html_page(PAGE)

    return httpx.Client(transport=httpx.MockTransport(serve))


def test_a_web_link_is_read_by_the_page_reader_and_never_offered_to_yt_dlp() -> None:
    # Setup
    asked: list[str] = []
    requests: list[httpx.Request] = []

    def extract(url: str) -> Mapping[str, object]:
        asked.append(url)
        return {"title": "Ramen crawl"}

    inspector = build_inspector(a_page_reader(requests), extract)

    # Execute
    info = inspector.inspect(PAGE_URL)

    # Assert
    assert (asked, len(requests), info.title) == ([], 1, "Ramen Tokyo")


def test_a_social_link_is_described_by_yt_dlp_without_reading_the_page() -> None:
    # Setup
    requests: list[httpx.Request] = []
    inspector = build_inspector(a_page_reader(requests), lambda url: {"title": "Ramen crawl"})

    # Execute
    info = inspector.inspect(VIDEO_URL)

    # Assert
    assert (requests, info.title) == ([], "Ramen crawl")


def test_a_hung_extractor_gives_an_unknown_link_within_the_deadline() -> None:
    # Setup
    hung = HungLinkInspector()
    inspector = build_inspector(
        a_page_reader([]),
        lambda url: {"title": hung.inspect(url).title},
        deadline_seconds=SHORT_DEADLINE_SECONDS,
    )

    # Execute
    info = inspector.inspect(VIDEO_URL)
    hung.release.set()

    # Assert
    assert info == LinkInfo.unknown(VIDEO_URL)


def test_the_inspection_deadline_is_25_seconds() -> None:
    # Assert
    assert INSPECTION_DEADLINE_SECONDS == 25.0
