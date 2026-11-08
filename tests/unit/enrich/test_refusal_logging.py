import logging

import httpx
from html_rig import FakeClock, build_html_rig, page_with_title, redirect_to
from log_records import recording_logs

from stash.enrich.html_meta import TOTAL_DEADLINE_SECONDS
from stash.enrich.ytdlp import YtDlpInspector

HTML_LOGGER = "stash.enrich.html_meta"
YTDLP_LOGGER = "stash.enrich.ytdlp"
PAGE_URL = "https://example.com/ramen"
PRIVATE_URL = "http://localhost:8080/admin?token=hidden"


def test_a_private_link_refused_by_the_extractor_guard_is_logged_at_info_with_its_host_only() -> (
    None
):
    # Setup
    inspector = YtDlpInspector(lambda url: {})

    # Execute
    with recording_logs(YTDLP_LOGGER) as recorder:
        inspector.inspect(PRIVATE_URL)

    # Assert
    assert recorder.entries() == [
        (logging.INFO, "yt-dlp skipped a non-public link: host localhost")
    ]


def test_a_private_link_refused_by_the_page_fetcher_is_logged_at_info_with_its_host_only() -> None:
    # Setup
    rig = build_html_rig()

    # Execute
    with recording_logs(HTML_LOGGER) as recorder:
        rig.inspector.inspect(PRIVATE_URL)

    # Assert
    assert recorder.entries() == [
        (logging.INFO, "page fetch skipped a non-public link: host localhost")
    ]


def test_a_redirect_to_a_private_host_is_logged_at_info_with_its_host_only() -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to("http://192.168.1.1/admin?token=hidden"))

    # Execute
    with recording_logs(HTML_LOGGER) as recorder:
        rig.inspector.inspect(PAGE_URL)

    # Assert
    assert recorder.entries() == [
        (logging.INFO, "page fetch refused a redirect to a non-public link: host 192.168.1.1")
    ]


def test_an_expired_total_deadline_while_streaming_is_logged_once_at_info() -> None:
    # Setup
    clock = FakeClock()

    def slow_page(request: httpx.Request) -> httpx.Response:
        clock.advance(TOTAL_DEADLINE_SECONDS)
        return page_with_title("Too late")

    rig = build_html_rig(slow_page, monotonic=clock)

    # Execute
    with recording_logs(HTML_LOGGER) as recorder:
        rig.inspector.inspect(PAGE_URL)

    # Assert
    assert recorder.entries() == [(logging.INFO, "page fetch gave up: total deadline passed")]


def test_an_expired_total_deadline_before_a_redirect_hop_is_logged_once_at_info() -> None:
    # Setup
    clock = FakeClock()

    def slow_redirect(request: httpx.Request) -> httpx.Response:
        clock.advance(TOTAL_DEADLINE_SECONDS)
        return redirect_to("/final")

    rig = build_html_rig(slow_redirect, monotonic=clock)

    # Execute
    with recording_logs(HTML_LOGGER) as recorder:
        rig.inspector.inspect(PAGE_URL)

    # Assert
    assert recorder.entries() == [(logging.INFO, "page fetch gave up: total deadline passed")]
