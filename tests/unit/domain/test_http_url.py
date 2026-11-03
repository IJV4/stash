import pytest

from stash.domain import http_url_host, require_http_url


@pytest.mark.parametrize(
    ("value", "host"),
    [
        ("https://example.com/a", "example.com"),
        ("http://example.com", "example.com"),
        ("HTTPS://Example.COM/Path", "example.com"),
        ("https://example.com:8443/a", "example.com"),
        ("https://user:pw@example.com/a", "example.com"),
        ("https://[::1]/a", "::1"),
        ("https://example.com./a", "example.com."),
    ],
)
def test_a_well_formed_http_or_https_url_yields_its_lower_case_host(value: str, host: str) -> None:
    # Execute / Assert
    assert http_url_host(value) == host


@pytest.mark.parametrize(
    "value",
    [
        "",
        "example.com",
        "ftp://example.com/a",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https:///path",
        "https://",
        "https://example.com:99999/",
        "https://example.com:abc/",
        "https://[::1/a",
        "https://exa mple.com/",
        "https://example.com/a b",
        "https://example.com/\n",
        "https://example.com/\x00",
        "\thttps://example.com/",
    ],
    ids=[
        "empty",
        "no-scheme",
        "ftp",
        "file",
        "javascript",
        "empty-host",
        "scheme-only",
        "port-out-of-range",
        "port-not-a-number",
        "unclosed-ipv6-bracket",
        "space-in-host",
        "space-in-path",
        "newline",
        "nul",
        "leading-tab",
    ],
)
def test_anything_but_a_well_formed_http_or_https_url_has_no_host(value: str) -> None:
    # Execute / Assert
    assert http_url_host(value) is None


def test_requiring_a_well_formed_url_accepts_it() -> None:
    # Execute / Assert
    assert require_http_url("url", "https://example.com/a") is None


def test_requiring_a_url_that_is_not_http_raises_value_error_naming_the_field() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="source_url must be an http"):
        require_http_url("source_url", "ftp://example.com")
