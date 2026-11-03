import pytest

from stash.domain import http_url_host

BACKSLASH_URLS = [
    "http://127.0.0.1\\.example.com/x",
    "http://127.0.0.1\\/",
    "http://169.254.169.254\\.x/",
    "http://localhost\\.com/",
]
COMPATIBILITY_URLS = [
    "http://127.0.0.1\uff3c.example.com/",
    "http://127.0.0.1\ufe68/",
    "http://127.0.0.1\u2100.example.com/",
    "http://127\uff052e0.0.1/",
    "http://127.0.0.1\u3000.example.com/",
]
PUNCTUATION = list("{}|^`~;!$&'()*+,=")


@pytest.mark.parametrize("value", BACKSLASH_URLS)
def test_a_host_containing_a_backslash_has_no_host(value: str) -> None:
    # Execute / Assert
    assert http_url_host(value) is None


@pytest.mark.parametrize("value", COMPATIBILITY_URLS)
def test_a_host_containing_a_compatibility_character_that_maps_to_a_separator_has_no_host(
    value: str,
) -> None:
    # Execute / Assert
    assert http_url_host(value) is None


@pytest.mark.parametrize("character", PUNCTUATION)
def test_a_host_name_containing_punctuation_has_no_host(character: str) -> None:
    # Execute / Assert
    assert http_url_host(f"http://exam{character}ple.com/") is None


@pytest.mark.parametrize("character", PUNCTUATION)
def test_an_ipv6_literal_containing_punctuation_has_no_host(character: str) -> None:
    # Execute / Assert
    assert http_url_host(f"http://[::1{character}]/") is None


def test_an_ipv6_literal_with_a_backslash_has_no_host() -> None:
    # Execute / Assert
    assert http_url_host("http://[::1\\]/") is None


@pytest.mark.parametrize(
    ("value", "host"),
    [
        ("http://my_host.example-site.com/", "my_host.example-site.com"),
        ("https://xn--bcher-kva.example/a", "xn--bcher-kva.example"),
        ("http://[2606:4700:4700::1111]/a", "2606:4700:4700::1111"),
        ("http://[::ffff:10.0.0.5]/a", "::ffff:10.0.0.5"),
    ],
)
def test_underscores_hyphens_punycode_and_ipv6_literals_remain_valid_hosts(
    value: str, host: str
) -> None:
    # Execute / Assert
    assert http_url_host(value) == host
