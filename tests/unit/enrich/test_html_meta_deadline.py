from collections.abc import Iterator

import httpx
from html_rig import FakeClock, build_html_rig, html_page, page_with_title, redirect_to

from stash.enrich.html_meta import TOTAL_DEADLINE_SECONDS
from stash.enrich.links import LinkInfo

PAGE_URL = "https://example.com/ramen"
TITLE_CHUNK = b"<html><head><title>Slow ramen</title></head><body>"
FILLER_CHUNK = b"<p>filler</p>"
FILLER_CHUNKS = 50


def dripping_page(
    clock: FakeClock, seconds_before_filler: float, read: list[int]
) -> httpx.Response:
    def chunks() -> Iterator[bytes]:
        yield TITLE_CHUNK
        clock.advance(seconds_before_filler)
        for number in range(FILLER_CHUNKS):
            read.append(number)
            yield FILLER_CHUNK

    return httpx.Response(200, headers={"content-type": "text/html"}, content=chunks())


def test_a_page_that_is_still_streaming_after_the_total_deadline_is_unknown() -> None:
    # Setup
    clock = FakeClock()
    rig = build_html_rig(
        lambda request: dripping_page(clock, TOTAL_DEADLINE_SECONDS, []), monotonic=clock
    )

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert info == LinkInfo.unknown(PAGE_URL)


def test_reading_stops_as_soon_as_the_total_deadline_passes() -> None:
    # Setup
    clock = FakeClock()
    read: list[int] = []
    rig = build_html_rig(
        lambda request: dripping_page(clock, TOTAL_DEADLINE_SECONDS, read), monotonic=clock
    )

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert len(read) <= 1


def test_a_page_that_finishes_just_inside_the_total_deadline_is_read() -> None:
    # Setup
    clock = FakeClock()
    rig = build_html_rig(
        lambda request: dripping_page(clock, TOTAL_DEADLINE_SECONDS - 1, []), monotonic=clock
    )

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert info.title == "Slow ramen"


def test_a_redirect_followed_after_the_total_deadline_is_never_requested() -> None:
    # Setup
    clock = FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        clock.advance(TOTAL_DEADLINE_SECONDS)
        return redirect_to("https://example.org/final")

    rig = build_html_rig(handler, monotonic=clock)

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


def test_a_redirect_chain_that_overruns_the_total_deadline_is_unknown() -> None:
    # Setup
    clock = FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        clock.advance(TOTAL_DEADLINE_SECONDS)
        if request.url.path == "/ramen":
            return redirect_to("/final")
        return page_with_title("Too late")

    rig = build_html_rig(handler, monotonic=clock)

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert info == LinkInfo.unknown(PAGE_URL)


def test_a_fast_page_is_read_in_full_under_the_default_clock() -> None:
    # Setup
    rig = build_html_rig(lambda request: html_page("<title>Quick</title>"))

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert info.title == "Quick"
