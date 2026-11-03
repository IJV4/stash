from collections.abc import Mapping

import pytest

from stash.enrich.links import LinkInfo
from stash.enrich.ytdlp import YtDlpInspector

DISGUISED_PRIVATE_URLS = [
    "http://127。0。0。1/a",
    "http://169。254。169。254/latest/meta-data",
    "http://localhost。/a",
    "http://x.local。/a",
]


@pytest.mark.parametrize("url", DISGUISED_PRIVATE_URLS)
def test_the_extractor_is_never_asked_about_a_link_hidden_behind_unicode_dots(url: str) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return {"title": "Private"}

    # Execute
    info = YtDlpInspector(extract).inspect(url)

    # Assert
    assert (asked, info) == ([], LinkInfo.unknown(url))


PERCENT_ENCODED_URLS = [
    "http://127%2e0%2e0%2e1:8000/x",
    "http://%6c%6f%63%61%6c%68%6f%73%74/",
    "http://localhost%2e/",
]


@pytest.mark.parametrize("url", PERCENT_ENCODED_URLS)
def test_the_extractor_is_never_asked_about_a_link_hidden_behind_percent_escapes(
    url: str,
) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return {"title": "Private"}

    # Execute
    with pytest.raises(ValueError, match="http"):
        YtDlpInspector(extract).inspect(url)

    # Assert
    assert asked == []


PARSER_DIFFERENTIAL_URLS = [
    "http://127.0.0.1\\.example.com/x",
    "http://127.0.0.1\\/",
    "http://169.254.169.254\\.x/",
    "http://localhost\\.com/",
    "http://exam|ple.com/",
]


@pytest.mark.parametrize("url", PARSER_DIFFERENTIAL_URLS)
def test_the_extractor_is_never_asked_about_a_host_outside_the_host_alphabet(
    url: str,
) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return {"title": "Private"}

    # Execute
    with pytest.raises(ValueError, match="http"):
        YtDlpInspector(extract).inspect(url)

    # Assert
    assert asked == []


@pytest.mark.parametrize("url", ["http://intranet/a", "http://instance-data/", "http://box.lan/a"])
def test_the_extractor_is_never_asked_about_a_dotless_or_home_network_host(url: str) -> None:
    # Setup
    asked: list[str] = []

    def extract(candidate: str) -> Mapping[str, object]:
        asked.append(candidate)
        return {"title": "Private"}

    # Execute
    info = YtDlpInspector(extract).inspect(url)

    # Assert
    assert (asked, info) == ([], LinkInfo.unknown(url))
