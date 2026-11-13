import httpx
import pytest
from html_rig import PUBLIC_ADDRESS, FakeResolver, build_html_rig, page_with_title, redirect_to

from stash.enrich.links import LinkInfo

PAGE_URL = "https://example.com/ramen"
OG_PAGE = (
    "<html><head><title>Plain title</title>"
    '<meta name="description" content="Plain description">'
    '<meta property="og:title" content="Ramen Tokyo">'
    '<meta property="og:description" content="Best bowls in Shibuya">'
    "</head><body>hello</body></html>"
)


def test_a_redirect_is_followed_to_the_final_page() -> None:
    # Setup
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ramen":
            return redirect_to("https://example.org/final")
        return page_with_title("Final")

    rig = build_html_rig(handler)

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert (info.title, rig.requested_urls()) == (
        "Final",
        [PAGE_URL, "https://example.org/final"],
    )


def test_a_relative_redirect_is_resolved_against_the_current_url() -> None:
    # Setup
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ramen":
            return redirect_to("/moved/here")
        return page_with_title("Moved")

    rig = build_html_rig(handler)

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL, "https://example.com/moved/here"]


def test_three_redirects_are_followed() -> None:
    # Setup
    def handler(request: httpx.Request) -> httpx.Response:
        hops = {"/ramen": "/1", "/1": "/2", "/2": "/3"}
        if request.url.path in hops:
            return redirect_to(hops[request.url.path])
        return page_with_title("Arrived")

    # Execute / Assert
    assert build_html_rig(handler).inspector.inspect(PAGE_URL).title == "Arrived"


def test_a_fourth_redirect_is_not_followed() -> None:
    # Setup
    def handler(request: httpx.Request) -> httpx.Response:
        hops = {"/ramen": "/1", "/1": "/2", "/2": "/3", "/3": "/4"}
        if request.url.path in hops:
            return redirect_to(hops[request.url.path])
        return page_with_title("Too far")

    rig = build_html_rig(handler)

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert (info, len(rig.requests)) == (LinkInfo.unknown(PAGE_URL), 4)


def test_a_redirect_loop_ends_as_unknown() -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(PAGE_URL))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


@pytest.mark.parametrize(
    "target",
    [
        "http://localhost:8080/admin",
        "http://127.0.0.1/admin",
        "http://192.168.1.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/admin",
        "ftp://example.com/file",
        "//10.0.0.5/admin",
    ],
)
def test_a_redirect_to_the_owners_network_or_a_non_http_scheme_is_never_requested(
    target: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


def test_a_redirect_to_the_owners_network_is_unknown() -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to("http://192.168.1.1/admin"))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


def test_a_redirect_with_an_unparseable_location_is_unknown() -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to("http://[::1"))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


@pytest.mark.parametrize(
    "url",
    ["http://localhost/a", "http://127.0.0.1:8080/a", "http://10.0.0.5/a", "http://my.local/a"],
)
def test_a_url_on_the_owners_network_is_never_requested(url: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    info = rig.inspector.inspect(url)

    # Assert
    assert (rig.requests, info) == ([], LinkInfo.unknown(url))


def test_a_redirect_to_a_host_the_http_client_cannot_build_is_unknown() -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to("https://xn--a.com/"))

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


DISGUISED_PRIVATE_URLS = [
    "http://127。0。0。1/admin",
    "http://169。254。169。254/latest/meta-data",
    "http://localhost。/admin",
    "http://x.local。/admin",
]


@pytest.mark.parametrize("url", DISGUISED_PRIVATE_URLS)
def test_a_url_on_the_owners_network_hidden_behind_unicode_dots_is_never_requested(
    url: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    info = rig.inspector.inspect(url)

    # Assert
    assert (rig.requests, info) == ([], LinkInfo.unknown(url))


@pytest.mark.parametrize("target", DISGUISED_PRIVATE_URLS)
def test_a_redirect_to_the_owners_network_hidden_behind_unicode_dots_is_never_requested(
    target: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


PERCENT_ENCODED_URLS = [
    "http://127%2e0%2e0%2e1:8000/x",
    "http://%6c%6f%63%61%6c%68%6f%73%74/",
    "http://localhost%2e/",
]


@pytest.mark.parametrize("url", PERCENT_ENCODED_URLS)
def test_a_url_hidden_behind_percent_escapes_is_never_requested(url: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    with pytest.raises(ValueError, match="http"):
        rig.inspector.inspect(url)

    # Assert
    assert rig.requests == []


@pytest.mark.parametrize("target", PERCENT_ENCODED_URLS)
def test_a_redirect_to_a_host_hidden_behind_percent_escapes_is_never_requested(
    target: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


PARSER_DIFFERENTIAL_URLS = [
    "http://127.0.0.1\\.example.com/x",
    "http://127.0.0.1\\/",
    "http://169.254.169.254\\.x/",
    "http://localhost\\.com/",
    "http://exam|ple.com/",
]
DOTLESS_OR_HOME_NETWORK_URLS = ["http://intranet/a", "http://instance-data/", "http://box.lan/a"]


@pytest.mark.parametrize("url", PARSER_DIFFERENTIAL_URLS)
def test_a_url_whose_host_has_a_character_outside_the_host_alphabet_is_never_requested(
    url: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    with pytest.raises(ValueError, match="http"):
        rig.inspector.inspect(url)

    # Assert
    assert rig.requests == []


@pytest.mark.parametrize("target", PARSER_DIFFERENTIAL_URLS)
def test_a_redirect_to_a_host_with_a_character_outside_the_host_alphabet_is_never_requested(
    target: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


@pytest.mark.parametrize("url", DOTLESS_OR_HOME_NETWORK_URLS)
def test_a_dotless_or_home_network_host_is_never_requested(url: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    info = rig.inspector.inspect(url)

    # Assert
    assert (rig.requests, info) == ([], LinkInfo.unknown(url))


@pytest.mark.parametrize("target", DOTLESS_OR_HOME_NETWORK_URLS)
def test_a_redirect_to_a_dotless_or_home_network_host_is_never_requested(target: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]


@pytest.mark.parametrize(
    "answers", [["127.0.0.1"], [PUBLIC_ADDRESS, "::1"], []], ids=["loopback", "mixed", "none"]
)
def test_a_name_that_does_not_resolve_only_to_public_addresses_is_not_fetched(
    answers: list[str],
) -> None:
    # Setup
    rig = build_html_rig(
        lambda request: page_with_title("Private"), resolve=FakeResolver({"example.com": answers})
    )

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert (rig.requests, info) == ([], LinkInfo.unknown(PAGE_URL))


def test_the_request_goes_to_the_checked_address_with_the_original_name_for_host_and_tls() -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Ramen"))

    # Execute
    rig.inspector.inspect("https://example.com:8443/ramen")

    # Assert
    request = rig.requests[0]
    assert (request.url.host, request.url.port, request.headers["host"]) == (
        PUBLIC_ADDRESS,
        8443,
        "example.com:8443",
    )
    assert request.extensions["sni_hostname"] == "example.com"


def test_each_redirect_hop_is_resolved_and_checked_again() -> None:
    # Setup
    resolver = FakeResolver({"other.example.org": ["10.0.0.5"]})
    rig = build_html_rig(
        lambda request: redirect_to("https://other.example.org/x"), resolve=resolver
    )

    # Execute
    info = rig.inspector.inspect(PAGE_URL)

    # Assert
    assert (info, resolver.calls, len(rig.requests)) == (
        LinkInfo.unknown(PAGE_URL),
        [("example.com", 443), ("other.example.org", 443)],
        1,
    )


def test_a_resolver_failure_gives_unknown_not_an_exception() -> None:
    # Setup
    rig = build_html_rig(
        lambda request: page_with_title("Ramen"), resolve=FakeResolver(error=OSError("no dns"))
    )

    # Execute / Assert
    assert rig.inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


@pytest.mark.parametrize("url", ["http://93.184.216.34/a", "https://[2606:2800:220:1::1]:8443/a"])
def test_a_public_address_link_is_fetched_without_asking_the_resolver(url: str) -> None:
    # Setup
    resolver = FakeResolver(error=OSError("must not be asked"))
    rig = build_html_rig(lambda request: page_with_title("Ramen"), resolve=resolver)

    # Execute
    info = rig.inspector.inspect(url)

    # Assert
    assert (info.title, resolver.calls) == ("Ramen", [])
