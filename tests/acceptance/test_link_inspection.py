from collections.abc import Mapping

import httpx
from html_rig import html_page, redirect_to
from link_rig import build_link_rig

from stash.enrich.links import LinkInfo

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
MOVED_URL = "https://example.com/moved"
LOCALHOST_URL = "http://localhost:8080/notes"
PRINTER_URL = "http://10.0.0.5/printer"


def test_a_link_yt_dlp_can_describe_yields_title_description_uploader_duration_and_captions() -> (
    None
):
    # Setup
    def extract(url: str) -> Mapping[str, object]:
        return {
            "title": "Ramen crawl",
            "description": "Five bowls in one night",
            "uploader": "Hana Eats",
            "duration": 61.5,
            "subtitles": {},
            "automatic_captions": {"en": [{"ext": "vtt"}]},
        }

    rig = build_link_rig(extract=extract)

    # Execute
    info = rig.inspector.inspect(VIDEO_URL)

    # Assert
    assert info == LinkInfo(
        url=VIDEO_URL,
        platform="youtube",
        title="Ramen crawl",
        description="Five bowls in one night",
        uploader="Hana Eats",
        duration_s=61,
        has_captions=True,
    )


def test_when_yt_dlp_fails_the_page_open_graph_tags_and_then_title_describe_the_link() -> None:
    # Setup
    page = (
        "<html><head><title>Plain title</title>"
        '<meta name="description" content="Plain description">'
        '<meta property="og:title" content="Ramen Tokyo">'
        '<meta property="og:description" content="Best bowls in Shibuya">'
        "</head></html>"
    )
    rig = build_link_rig(handler=lambda request: html_page(page))

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert (info.title, info.description) == ("Ramen Tokyo", "Best bowls in Shibuya")


def test_when_neither_yt_dlp_nor_the_page_can_describe_the_link_only_the_platform_is_filled() -> (
    None
):
    # Setup
    rig = build_link_rig()

    # Execute
    info = rig.inspector.inspect(VIDEO_URL)

    # Assert
    assert info == LinkInfo(
        url=VIDEO_URL,
        platform="youtube",
        title=None,
        description=None,
        uploader=None,
        duration_s=None,
        has_captions=False,
    )


def test_a_link_to_the_owners_own_network_and_a_redirect_leading_there_are_never_fetched() -> None:
    # Setup
    def public_page_and_a_redirect_to_the_router(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/moved":
            return redirect_to("http://192.168.1.1/admin")
        return html_page("<html><head><title>Ramen Tokyo</title></head></html>")

    rig = build_link_rig(handler=public_page_and_a_redirect_to_the_router)

    # Execute
    on_localhost = rig.inspector.inspect(LOCALHOST_URL)
    on_the_lan = rig.inspector.inspect(PRINTER_URL)
    redirected = rig.inspector.inspect(MOVED_URL)
    public = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert on_localhost == LinkInfo.unknown(LOCALHOST_URL)
    assert on_the_lan == LinkInfo.unknown(PRINTER_URL)
    assert redirected == LinkInfo.unknown(MOVED_URL)
    assert public.title == "Ramen Tokyo"
    assert rig.extracted == [MOVED_URL, PAGE_URL]
    assert rig.requested_hosts() == ["example.com", "example.com"]
