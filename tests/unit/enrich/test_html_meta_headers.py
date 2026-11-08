import pytest

from stash.enrich.html_meta import REQUEST_HEADERS


def test_the_request_headers_cannot_be_changed() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        REQUEST_HEADERS["Accept"] = "*/*"  # type: ignore[index]
