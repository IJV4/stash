import pytest

from stash.domain import http_url_host


@pytest.mark.parametrize(
    ("value", "host"),
    [
        ("http://127。0。0。1/", "127.0.0.1"),
        ("http://127\uff0e0\uff0e0\uff0e1/", "127.0.0.1"),
        ("http://localhost。/", "localhost."),
        ("https://bücher.example/a", "xn--bcher-kva.example"),
        ("https://[::1]/a", "::1"),
    ],
)
def test_a_host_is_yielded_in_its_ascii_idna_form(value: str, host: str) -> None:
    # Execute / Assert
    assert http_url_host(value) == host


@pytest.mark.parametrize(
    "value",
    ["http://exa..mple.com/", f"http://{'a' * 64}.example/"],
    ids=["empty-label", "label-over-63-characters"],
)
def test_a_host_that_cannot_be_idna_encoded_has_no_host(value: str) -> None:
    # Execute / Assert
    assert http_url_host(value) is None
