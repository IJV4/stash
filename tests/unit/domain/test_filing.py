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


def test_filing_planned_with_a_date_is_accepted() -> None:
    # Setup / Execute
    filing = a_filing(stage=Stage.PLANNED, date=PLANNED_FOR)

    # Assert
    assert filing.date == PLANNED_FOR


def test_filing_unplanned_without_a_date_is_accepted() -> None:
    # Setup / Execute
    filing = a_filing(stage=Stage.INBOX, date=None)

    # Assert
    assert filing.date is None


def test_filing_details_do_not_change_when_the_source_dict_is_mutated() -> None:
    # Setup
    source = {"city": "Tokyo"}
    filing = a_filing(details=source)

    # Execute
    source["city"] = "Osaka"

    # Assert
    assert dict(filing.details) == {"city": "Tokyo"}


def test_filing_details_cannot_be_modified_through_the_filing() -> None:
    # Setup
    filing = a_filing(details={"city": "Tokyo"})

    # Execute / Assert
    with pytest.raises(TypeError):
        filing.details["city"] = "Osaka"  # type: ignore[index]


def test_filings_built_from_equal_details_are_equal() -> None:
    # Setup
    first = a_filing(details={"city": "Tokyo"})
    second = a_filing(details={"city": "Tokyo"})

    # Assert
    assert first == second


def test_filing_tags_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    tags = ["food"]
    filing = a_filing(tags=tags)

    # Execute
    tags.append("ramen")

    # Assert
    assert filing == a_filing(tags=("food",))


def test_filing_people_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    people = ["Ana"]
    filing = a_filing(people=people)

    # Execute
    people.append("Ben")

    # Assert
    assert filing == a_filing(people=("Ana",))


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
