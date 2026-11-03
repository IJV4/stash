from collections.abc import Mapping

import pytest
from html_rig import build_html_rig, page_with_title, redirect_to

from stash.enrich.links import LinkInfo
from stash.enrich.ytdlp import YtDlpInspector

PAGE_URL = "https://example.com/ramen"
LOCAL_ALIAS_URLS = [
    "http://localhost.localdomain:8080/admin",
    "http://x.localdomain/",
    "http://db.default.svc/",
]


@pytest.mark.parametrize("url", LOCAL_ALIAS_URLS)
def test_the_extractor_is_never_asked_about_a_local_alias_or_cluster_service_host(
    url: str,
) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return {"title": "Private"}

    # Execute
    info = YtDlpInspector(extract).inspect(url)

    # Assert
    assert (asked, info) == ([], LinkInfo.unknown(url))


@pytest.mark.parametrize("url", LOCAL_ALIAS_URLS)
def test_a_local_alias_or_cluster_service_host_is_never_requested(url: str) -> None:
    # Setup
    rig = build_html_rig(lambda request: page_with_title("Private"))

    # Execute
    info = rig.inspector.inspect(url)

    # Assert
    assert (rig.requests, info) == ([], LinkInfo.unknown(url))


@pytest.mark.parametrize("target", LOCAL_ALIAS_URLS)
def test_a_redirect_to_a_local_alias_or_cluster_service_host_is_never_requested(
    target: str,
) -> None:
    # Setup
    rig = build_html_rig(lambda request: redirect_to(target))

    # Execute
    rig.inspector.inspect(PAGE_URL)

    # Assert
    assert rig.requested_urls() == [PAGE_URL]
