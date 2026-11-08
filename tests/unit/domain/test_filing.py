from datetime import date

import pytest
from builders import BASE, a_filing

from stash.domain.item import Stage

PLANNED_FOR = date(2026, 11, 14)


def test_filing_with_empty_title_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="title"):
        a_filing(title="")


def test_filing_with_whitespace_only_title_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="title"):
        a_filing(title="  \t ")


def test_filing_planned_without_a_date_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="planned items need a date"):
        a_filing(stage=Stage.PLANNED, date=None)


def test_filing_tags_given_a_bare_string_raise_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="tags must be a collection of strings"):
        a_filing(tags="food")


def test_filing_people_given_a_bare_string_raise_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="people must be a collection of strings"):
        a_filing(people="ab")


def test_filing_with_a_datetime_for_date_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="date must be a date, not a datetime"):
        a_filing(date=BASE)
