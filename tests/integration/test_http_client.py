import httpx
import pytest

from stash.http_client import make_http_client


@pytest.mark.integration
def test_the_http_client_allows_two_minutes_to_answer_and_ten_seconds_to_connect() -> None:
    # Setup
    client = make_http_client()

    # Execute
    timeout = client.timeout
    client.close()

    # Assert
    assert timeout == httpx.Timeout(120.0, connect=10.0)


@pytest.mark.integration
def test_the_http_client_has_no_base_url_so_one_client_serves_every_provider() -> None:
    # Setup
    client = make_http_client()

    # Execute
    base_url = client.base_url
    client.close()

    # Assert
    assert base_url == httpx.URL("")


@pytest.mark.integration
def test_the_http_client_never_follows_redirects_so_the_bearer_key_stays_on_its_host() -> None:
    # Setup
    client = make_http_client()

    # Execute
    follows_redirects = client.follow_redirects
    client.close()

    # Assert
    assert follows_redirects is False
