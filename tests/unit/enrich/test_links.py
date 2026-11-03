from dataclasses import FrozenInstanceError

import pytest
from fakes.link_inspector import FakeLinkInspector
from link_builders import VIDEO_URL, a_link_info

from stash.enrich.links import TITLE_LIMIT, FallbackInspector, LinkInfo

PAGE_URL = "https://example.com/ramen"


def test_a_link_info_with_a_url_that_is_not_http_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="url"):
        a_link_info(url="ftp://example.com/a")


def test_a_link_info_with_an_unknown_platform_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="platform"):
        a_link_info(platform="myspace")


@pytest.mark.parametrize("duration", [-1, 61.5, True, "61"])
def test_a_link_info_with_a_duration_that_is_not_a_non_negative_int_raises_value_error(
    duration: object,
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="duration_s"):
        a_link_info(duration_s=duration)


def test_a_link_info_with_a_zero_second_duration_is_accepted() -> None:
    # Execute / Assert
    assert a_link_info(duration_s=0).duration_s == 0


@pytest.mark.parametrize(
    ("field", "limit"), [("title", 300), ("description", 2000), ("uploader", 200)]
)
def test_a_link_info_text_field_is_clipped_to_its_limit(field: str, limit: int) -> None:
    # Execute
    info = a_link_info(**{field: "x" * (limit + 50)})

    # Assert
    assert getattr(info, field) == "x" * limit


@pytest.mark.parametrize("field", ["title", "description", "uploader"])
def test_a_link_info_text_field_has_its_whitespace_collapsed(field: str) -> None:
    # Execute
    info = a_link_info(**{field: "  two \n\n lines\t here "})

    # Assert
    assert getattr(info, field) == "two lines here"


@pytest.mark.parametrize("field", ["title", "description", "uploader"])
def test_a_link_info_blank_text_field_becomes_none(field: str) -> None:
    # Execute
    info = a_link_info(**{field: " \n\t "})

    # Assert
    assert getattr(info, field) is None


def test_a_link_info_cannot_be_changed_after_creation() -> None:
    # Setup
    info = a_link_info()

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        info.title = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("url", "platform"), [(VIDEO_URL, "youtube"), (PAGE_URL, "web"), ("https://x.com/a/1", "x")]
)
def test_an_unknown_link_info_carries_only_the_platform_of_the_host(
    url: str, platform: str
) -> None:
    # Execute / Assert
    assert LinkInfo.unknown(url) == LinkInfo(
        url=url,
        platform=platform,
        title=None,
        description=None,
        uploader=None,
        duration_s=None,
        has_captions=False,
    )


def test_the_fallback_inspector_returns_the_first_result_when_it_has_a_title() -> None:
    # Setup
    first_info = a_link_info(title="From first")
    inspector = FallbackInspector(
        FakeLinkInspector({VIDEO_URL: first_info}),
        FakeLinkInspector({VIDEO_URL: a_link_info(title="From second")}),
    )

    # Execute / Assert
    assert inspector.inspect(VIDEO_URL) == first_info


def test_the_fallback_inspector_does_not_ask_the_second_when_the_first_has_a_title() -> None:
    # Setup
    second = FakeLinkInspector()
    inspector = FallbackInspector(FakeLinkInspector({VIDEO_URL: a_link_info()}), second)

    # Execute
    inspector.inspect(VIDEO_URL)

    # Assert
    assert second.inspected == []


def test_the_fallback_inspector_returns_the_second_result_when_the_first_has_no_title() -> None:
    # Setup
    second_info = a_link_info(title="From second")
    inspector = FallbackInspector(
        FakeLinkInspector({VIDEO_URL: a_link_info(title=None)}),
        FakeLinkInspector({VIDEO_URL: second_info}),
    )

    # Execute / Assert
    assert inspector.inspect(VIDEO_URL) == second_info


def test_the_fallback_inspector_returns_the_second_result_even_when_that_is_unknown() -> None:
    # Setup
    inspector = FallbackInspector(FakeLinkInspector(), FakeLinkInspector())

    # Execute / Assert
    assert inspector.inspect(PAGE_URL) == LinkInfo.unknown(PAGE_URL)


def test_a_page_link_info_carries_the_title_and_description_and_the_platform_of_the_host() -> None:
    # Execute / Assert
    assert LinkInfo.from_page(VIDEO_URL, "A title", "A description") == LinkInfo(
        url=VIDEO_URL,
        platform="youtube",
        title="A title",
        description="A description",
        uploader=None,
        duration_s=None,
        has_captions=False,
    )


def test_a_page_link_info_without_title_or_description_equals_the_unknown_one() -> None:
    # Execute / Assert
    assert LinkInfo.from_page(PAGE_URL, None, None) == LinkInfo.unknown(PAGE_URL)


def test_a_page_link_info_clamps_an_overlong_title() -> None:
    # Execute
    info = LinkInfo.from_page(PAGE_URL, "t" * (TITLE_LIMIT + 50), None)

    # Assert
    assert info.title == "t" * TITLE_LIMIT
