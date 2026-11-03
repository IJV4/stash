import pytest

from stash.domain import http_url_host

PERCENT_ENCODED_HOSTS = [
    "http://127%2e0%2e0%2e1:8000/x",
    "http://%6c%6f%63%61%6c%68%6f%73%74/",
    "http://localhost%2e/",
    "https://exa%6dple.com/a",
]


@pytest.mark.parametrize("value", PERCENT_ENCODED_HOSTS)
def test_a_host_containing_a_percent_escape_has_no_host(value: str) -> None:
    # Execute / Assert
    assert http_url_host(value) is None


def test_a_percent_escape_in_the_path_does_not_hide_the_host() -> None:
    # Execute / Assert
    assert http_url_host("https://example.com/a%20b?q=%2e") == "example.com"
