from datetime import date

import pytest

from stash.capture.callbacks import (
    FixAction,
    FixKind,
    date_for,
)

A_DAY = date(2027, 2, 13)


def test_the_not_happened_kind_travels_as_h() -> None:
    # Execute / Assert
    assert FixKind.NOT_HAPPENED.value == "h"


def test_a_not_happened_action_without_a_date_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="argument presence"):
        FixAction(FixKind.NOT_HAPPENED, "i1")


@pytest.mark.parametrize("argument", [None, "", "2027-02-13", "20271301", "2027021", "202702130"])
def test_an_argument_that_is_not_a_yyyymmdd_day_reads_as_no_day(argument: str | None) -> None:
    # Execute / Assert
    assert date_for(argument) is None
