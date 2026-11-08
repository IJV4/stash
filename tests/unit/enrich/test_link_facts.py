import pytest
from link_builders import a_link_info

from stash.domain import DETAIL_VALUE_LIMIT

LONG_TEXT = "word " * 10_000


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [
        (0, "0:00"),
        (9, "0:09"),
        (59, "0:59"),
        (60, "1:00"),
        (754, "12:34"),
        (3599, "59:59"),
        (3600, "1:00:00"),
        (3723, "1:02:03"),
        (36000, "10:00:00"),
        (360000, "100:00:00"),
    ],
)
def test_the_duration_is_shown_as_minutes_and_seconds_under_an_hour_and_hours_from_there(
    seconds: int, shown: str
) -> None:
    # Setup
    info = a_link_info(duration_s=seconds)

    # Execute
    facts = info.facts()

    # Assert
    assert facts["duration"] == shown


@pytest.mark.parametrize("field", ["title", "uploader"])
def test_a_text_the_link_itself_let_through_too_long_is_clipped_to_the_details_value_limit(
    field: str,
) -> None:
    # Setup
    info = a_link_info()
    object.__setattr__(info, field, LONG_TEXT)

    # Execute
    facts = info.facts()

    # Assert
    assert max(len(text) for text in facts.values()) <= DETAIL_VALUE_LIMIT
