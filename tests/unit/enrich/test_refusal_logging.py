import logging

import httpx
from html_rig import FakeClock, build_html_rig, page_with_title, redirect_to
from log_records import recording_logs

from stash.enrich.html_meta import TOTAL_DEADLINE_SECONDS

HTML_LOGGER = "stash.enrich.html_meta"
PAGE_URL = "https://example.com/ramen"


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
