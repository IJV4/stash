import pytest
from link_builders import a_link_info

from stash.enrich.links import TITLE_LIMIT, LinkInfo

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


def test_a_page_link_info_clamps_an_overlong_title() -> None:
    # Execute
    info = LinkInfo.from_page(PAGE_URL, "t" * (TITLE_LIMIT + 50), None)

    # Assert
    assert info.title == "t" * TITLE_LIMIT
