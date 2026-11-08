import pytest
from link_builders import a_link_info

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
