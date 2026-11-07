from datetime import date

import pytest
from builders import HEX_ID, MAX_LENGTH_ID

from stash.capture.callbacks import (
    TELEGRAM_CALLBACK_LIMIT,
    FixAction,
    FixKind,
    date_argument,
    date_for,
)

A_DAY = date(2027, 2, 13)


def test_the_not_happened_kind_travels_as_h() -> None:
    # Execute / Assert
    assert FixKind.NOT_HAPPENED.value == "h"


def test_not_happened_encodes_the_date_it_was_asked_about_in_its_wire_format() -> None:
    # Execute / Assert
    assert FixAction(FixKind.NOT_HAPPENED, "i1", date_argument(A_DAY)).encode() == (
        "stash:h:i1:20270213"
    )


def test_a_not_happened_wire_string_parses_back_to_its_action() -> None:
    # Execute / Assert
    assert FixAction.parse("stash:h:i1:20270213") == FixAction(
        FixKind.NOT_HAPPENED, "i1", "20270213"
    )


def test_the_not_happened_kind_takes_an_argument() -> None:
    # Execute / Assert
    assert FixKind.NOT_HAPPENED.takes_argument is True


def test_a_not_happened_action_without_a_date_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(FixKind.NOT_HAPPENED, "i1")


@pytest.mark.parametrize("subject_id", [HEX_ID, MAX_LENGTH_ID])
def test_a_not_happened_action_for_the_longest_ids_fits_the_telegram_callback_limit(
    subject_id: str,
) -> None:
    # Execute
    data = FixAction(FixKind.NOT_HAPPENED, subject_id, date_argument(A_DAY)).encode()

    # Assert
    assert len(data.encode("utf-8")) <= TELEGRAM_CALLBACK_LIMIT


def test_a_date_argument_reads_back_as_the_same_day() -> None:
    # Execute / Assert
    assert date_for(date_argument(A_DAY)) == A_DAY


@pytest.mark.parametrize("argument", [None, "", "2027-02-13", "20271301", "2027021", "202702130"])
def test_an_argument_that_is_not_a_yyyymmdd_day_reads_as_no_day(argument: str | None) -> None:
    # Execute / Assert
    assert date_for(argument) is None
