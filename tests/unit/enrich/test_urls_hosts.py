import pytest

from stash.enrich import extract_urls, is_public_http_url

BACKSLASH_URLS = [
    "http://127.0.0.1\\.example.com/x",
    "http://127.0.0.1\\/",
    "http://169.254.169.254\\.x/",
    "http://localhost\\.com/",
]
PUNCTUATION_URLS = [f"http://exam{c}ple.com/" for c in "{}|^`~;!$&'()*+,="]
DOTLESS_URLS = [
    "http://intranet/",
    "http://nas/a",
    "http://router:8080/",
    "http://instance-data/latest",
    "http://kubernetes/",
    "http://host/",
    "http://intranet./",
]
PRIVATE_SUFFIX_URLS = [
    "http://box.lan/",
    "http://box.home.arpa/",
    "http://wiki.intranet/",
    "http://files.corp/",
    "http://db.private/",
    "http://tv.home/",
]
LOCAL_ALIAS_URLS = [
    "http://localhost.localdomain:8080/admin",
    "http://x.localdomain/",
    "http://db.default.svc/",
]
MULTICAST_URLS = ["http://224.0.0.1/", "http://239.255.255.250/", "http://[ff02::1]/"]


@pytest.mark.parametrize("url", [*BACKSLASH_URLS, *PUNCTUATION_URLS])
def test_a_url_whose_host_contains_a_character_outside_the_host_alphabet_is_not_public(
    url: str,
) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False


@pytest.mark.parametrize("url", BACKSLASH_URLS)
def test_a_link_whose_host_contains_a_backslash_is_not_a_link(url: str) -> None:
    # Execute / Assert
    assert extract_urls(f"see {url} now") == ()


@pytest.mark.parametrize("url", DOTLESS_URLS)
def test_a_host_without_a_dot_is_not_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False


def test_a_fully_qualified_host_with_a_trailing_dot_is_still_public() -> None:
    # Execute / Assert
    assert is_public_http_url("http://example.com./") is True


@pytest.mark.parametrize("url", PRIVATE_SUFFIX_URLS)
def test_a_host_under_a_home_or_office_network_suffix_is_not_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False


@pytest.mark.parametrize("url", MULTICAST_URLS)
def test_a_multicast_address_is_not_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False


@pytest.mark.parametrize("url", LOCAL_ALIAS_URLS)
def test_a_local_alias_or_cluster_service_host_is_not_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False


def test_a_url_written_with_ideographic_full_stops_is_judged_by_the_address_it_spells() -> None:
    # Execute / Assert
    assert is_public_http_url("http://127\u30020\u30020\u30021/") is False
