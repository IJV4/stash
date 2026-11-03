import pytest
from fakes.link_inspector import FakeLinkInspector
from link_builders import VIDEO_URL, a_link_info

from stash.enrich.links import LinkInfo
from stash.enrich.platform_scope import KnownPlatformsOnly

PAGE_URL = "https://example.com/ramen-tokyo"
KNOWN_PLATFORM_URLS = [
    "https://www.instagram.com/p/abc/",
    VIDEO_URL,
    "https://youtu.be/abc123",
    "https://www.tiktok.com/@hana/video/1",
    "https://x.com/hana/status/1",
    "https://www.reddit.com/r/ramen/comments/abc/",
]


def test_a_web_link_is_unknown_without_asking_the_inner_inspector() -> None:
    # Setup
    inner = FakeLinkInspector()

    # Execute
    info = KnownPlatformsOnly(inner).inspect(PAGE_URL)

    # Assert
    assert (info, inner.inspected) == (LinkInfo.unknown(PAGE_URL), [])


def test_a_link_from_a_known_platform_is_described_by_the_inner_inspector() -> None:
    # Setup
    described = a_link_info()
    inner = FakeLinkInspector({VIDEO_URL: described})

    # Execute
    info = KnownPlatformsOnly(inner).inspect(VIDEO_URL)

    # Assert
    assert info == described


@pytest.mark.parametrize("url", KNOWN_PLATFORM_URLS)
def test_every_known_platform_is_passed_to_the_inner_inspector(url: str) -> None:
    # Setup
    inner = FakeLinkInspector()

    # Execute
    KnownPlatformsOnly(inner).inspect(url)

    # Assert
    assert inner.inspected == [url]
