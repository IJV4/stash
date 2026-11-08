import gzip
import logging
from collections.abc import Iterator

import httpx
import pytest
from html_rig import build_html_rig, html_page

from stash.enrich.links import LinkInfo

PAGE_URL = "https://example.com/ramen"
HTML = {"content-type": "text/html"}
HALF_A_MEBIBYTE = 512 * 1024
OG_PAGE = (
    "<html><head><title>Plain title</title>"
    '<meta name="description" content="Plain description">'
    '<meta property="og:title" content="Ramen Tokyo">'
    '<meta property="og:description" content="Best bowls in Shibuya">'
    "</head><body>hello</body></html>"
)


def inspect_page(body: str, url: str = PAGE_URL) -> LinkInfo:
    return build_html_rig(lambda request: html_page(body)).inspector.inspect(url)


def test_an_xhtml_response_is_read() -> None:
    # Setup
    rig = build_html_rig(lambda request: html_page(OG_PAGE, "application/xhtml+xml"))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL).title == "Ramen Tokyo"


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), httpx.RemoteProtocolError("bad")],
)
def test_a_transport_failure_is_unknown(error: httpx.HTTPError) -> None:
    # Setup
    def fail(request: httpx.Request) -> httpx.Response:
        raise error

    # Execute / Assert
    assert build_html_rig(fail).inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


def test_a_failed_fetch_is_logged_as_a_warning_naming_only_the_error_class(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Setup
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret-host-detail")

    # Execute
    build_html_rig(fail).inspector.inspect(f"{PAGE_URL}?token=hidden")

    # Assert
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, "page fetch failed: ConnectError")
    ]


def test_a_page_whose_title_lies_beyond_the_size_limit_is_unknown() -> None:
    # Setup
    padding = "x" * HALF_A_MEBIBYTE

    # Execute / Assert
    assert inspect_page(f"<p>{padding}</p><title>Late</title>") == LinkInfo.unknown(PAGE_URL)


def test_a_title_in_a_page_far_larger_than_the_limit_is_still_read() -> None:
    # Setup
    head = "<title>Early</title>"

    # Execute / Assert
    assert inspect_page(head + "x" * (HALF_A_MEBIBYTE * 2)).title == "Early"


def test_a_title_ending_just_inside_the_size_limit_is_read() -> None:
    # Setup
    title = "<title>Inside</title>"
    page = "x" * (HALF_A_MEBIBYTE - len(title) - 10) + title + "x" * 100

    # Execute / Assert
    assert inspect_page(page).title == "Inside"


def test_reading_stops_once_the_size_limit_is_reached() -> None:
    # Setup
    chunk = b"x" * 65536
    chunks_read: list[int] = []

    def endless() -> Iterator[bytes]:
        for number in range(1000):
            chunks_read.append(number)
            yield chunk

    rig = build_html_rig(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/html"}, content=endless()
        )
    )

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert len(chunks_read) == HALF_A_MEBIBYTE // len(chunk)


def test_a_gzip_encoded_page_is_decoded_before_it_is_parsed() -> None:
    # Setup
    body = gzip.compress(OG_PAGE.encode())
    headers = {"content-type": "text/html", "content-encoding": "gzip"}
    rig = build_html_rig(lambda request: httpx.Response(200, headers=headers, content=body))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL).title == "Ramen Tokyo"


def test_a_page_with_an_unknown_charset_is_decoded_as_utf_8() -> None:
    # Setup
    headers = {"content-type": "text/html; charset=no-such-charset"}
    body = "<title>Café</title>".encode()
    rig = build_html_rig(lambda request: httpx.Response(200, headers=headers, content=body))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL).title == "Café"


@pytest.mark.parametrize(
    "url",
    ["https://example.com/" + "a" * 70000, "https://xn--a.com/"],
    ids=["overlong", "invalid-punycode-host"],
)
def test_a_url_the_http_client_cannot_build_is_unknown(url: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: html_page(OG_PAGE))

    # Execute / Assert
    assert rig.inspector.inspect(url) == LinkInfo.unknown(url)
