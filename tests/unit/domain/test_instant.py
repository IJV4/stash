from datetime import UTC, datetime

import pytest
from builders import BASE, PLUS_FIVE

from stash.domain import utc_text


def test_a_utc_moment_is_written_with_microseconds_and_a_zero_offset() -> None:
    # Execute
    text = utc_text(BASE)

    # Assert
    assert text == "2026-11-02T12:00:00.000000+00:00"


def test_a_moment_in_another_offset_is_written_in_utc() -> None:
    # Setup
    moment = datetime(2026, 11, 2, 17, 0, tzinfo=PLUS_FIVE)

    # Execute
    text = utc_text(moment)

    # Assert
    assert text == "2026-11-02T12:00:00.000000+00:00"


def test_the_same_instant_in_two_offsets_gives_the_same_text() -> None:
    # Setup
    in_utc = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    in_plus_five = in_utc.astimezone(PLUS_FIVE)

    # Execute / Assert
    assert utc_text(in_plus_five) == utc_text(in_utc)


def test_microseconds_survive_the_conversion() -> None:
    # Execute
    text = utc_text(datetime(2026, 11, 2, 12, 0, 0, 123456, tzinfo=UTC))

    # Assert
    assert text == "2026-11-02T12:00:00.123456+00:00"


def test_a_naive_moment_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="moment"):
        utc_text(datetime(2026, 11, 2, 12, 0))
