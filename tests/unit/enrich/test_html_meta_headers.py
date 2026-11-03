import pytest
from html_rig import build_html_rig, not_found

from stash.enrich.html_meta import REQUEST_HEADERS


def test_the_request_headers_cannot_be_changed() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        REQUEST_HEADERS["Accept"] = "*/*"  # type: ignore[index]


def test_the_request_asks_for_an_uncompressed_body() -> None:
    # Setup
    rig = build_html_rig(not_found)

    # Execute
    rig.inspector.inspect("https://example.com/ramen")

    # Assert
    assert rig.requests[0].headers["accept-encoding"] == "identity"
