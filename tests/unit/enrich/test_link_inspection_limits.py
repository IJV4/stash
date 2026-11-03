from collections.abc import Mapping

import httpx
from capture_builders import RAMEN_URL, a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.hung_link_inspector import HungLinkInspector
from fakes.memory_store import MemoryStore
from html_rig import html_page

from stash.capture import Filed
from stash.enrich.deadline import DeadlineInspector
from stash.enrich.html_meta import HtmlMetaInspector
from stash.enrich.links import FallbackInspector, LinkInfo
from stash.enrich.platform_scope import KnownPlatformsOnly
from stash.enrich.ytdlp import YtDlpInspector

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
SHORT_DEADLINE_SECONDS = 0.005


def test_yt_dlp_is_only_asked_about_known_platforms_and_other_links_go_to_the_page_reader() -> None:
    # Setup
    asked: list[str] = []

    def extract(url: str) -> Mapping[str, object]:
        asked.append(url)
        return {"title": "Ramen crawl"}

    page = "<html><head><title>Ramen Tokyo</title></head></html>"
    client = httpx.Client(transport=httpx.MockTransport(lambda request: html_page(page)))
    inspector = FallbackInspector(
        KnownPlatformsOnly(YtDlpInspector(extract)), HtmlMetaInspector(client)
    )

    # Execute
    video = inspector.inspect(VIDEO_URL)
    web = inspector.inspect(PAGE_URL)

    # Assert
    assert (asked, video.title, web.title) == ([VIDEO_URL], "Ramen crawl", "Ramen Tokyo")


def test_a_link_that_takes_too_long_to_inspect_is_filed_from_the_owners_own_words() -> None:
    # Setup
    hung = HungLinkInspector()
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(MemoryStore(), DeadlineInspector(hung, SHORT_DEADLINE_SECONDS), filer)

    # Execute
    result = pipeline.handle(a_message(f"{RAMEN_URL} try this in March"))
    hung.release.set()

    # Assert
    assert isinstance(result, Filed)
    assert filer.calls == [(f"{RAMEN_URL} try this in March", LinkInfo.unknown(RAMEN_URL))]
