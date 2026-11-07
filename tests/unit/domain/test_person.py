from datetime import date
from typing import Any

import pytest
from builders import NAIVE
from people_builders import a_key_date, a_person

from stash.domain import (
    KEY_DATE_LABEL_LIMIT,
    MAX_ALIASES,
    PERSON_NAME_LIMIT,
    PERSON_NOTES_LIMIT,
    PERSON_RELATION_LIMIT,
    KeyDateKind,
)

BARE_STRING_ALIASES: Any = "Anita"


def test_a_person_keeps_the_aliases_it_was_given() -> None:
    # Execute
    person = a_person(aliases=["Anita", "Ani"])

    # Assert
    assert person.aliases == ("Anita", "Ani")


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"name": "x" * (PERSON_NAME_LIMIT + 1)},
        {"relation": "x" * (PERSON_RELATION_LIMIT + 1)},
        {"aliases": tuple(f"alias {number}" for number in range(MAX_ALIASES + 1))},
        {"aliases": ("  ",)},
        {"aliases": ("x" * (PERSON_NAME_LIMIT + 1),)},
        {"notes": "x" * (PERSON_NOTES_LIMIT + 1)},
        {"created_at": NAIVE},
        {"id": "two words"},
    ],
    ids=[
        "blank-name",
        "long-name",
        "long-relation",
        "too-many-aliases",
        "blank-alias",
        "long-alias",
        "long-notes",
        "naive-created-at",
        "unsafe-id",
    ],
)
def test_a_person_that_breaks_a_limit_is_refused(overrides: dict[str, Any]) -> None:
    # Execute / Assert
    with pytest.raises(ValueError):
        a_person(**overrides)


def test_a_person_given_a_bare_string_for_aliases_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        a_person(aliases=BARE_STRING_ALIASES)


def test_a_person_with_all_text_at_its_limits_is_accepted() -> None:
    # Execute
    person = a_person(
        name="x" * PERSON_NAME_LIMIT,
        relation="x" * PERSON_RELATION_LIMIT,
        aliases=("x" * PERSON_NAME_LIMIT,) * MAX_ALIASES,
        notes="x" * PERSON_NOTES_LIMIT,
    )

    # Assert
    assert len(person.aliases) == MAX_ALIASES


@pytest.mark.parametrize(
    "overrides",
    [
        {"month": 13},
        {"month": 0},
        {"day": 0},
        {"month": 4, "day": 31},
        {"month": 2, "day": 30},
        {"month": 2, "day": 29, "year": 2023},
        {"year": 0},
        {"label": "x" * (KEY_DATE_LABEL_LIMIT + 1)},
        {"id": "two words"},
        {"person_id": "two words"},
    ],
    ids=[
        "month-13",
        "month-0",
        "day-0",
        "april-31",
        "february-30",
        "february-29-in-a-common-year",
        "year-0",
        "long-label",
        "unsafe-id",
        "unsafe-person-id",
    ],
)
def test_a_key_date_that_is_not_a_real_calendar_date_is_refused(
    overrides: dict[str, Any],
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError):
        a_key_date(**overrides)


@pytest.mark.parametrize("year", [None, 2000])
def test_february_29_is_a_valid_key_date(year: int | None) -> None:
    # Execute
    key_date = a_key_date(month=2, day=29, year=year)

    # Assert
    assert (key_date.month, key_date.day) == (2, 29)


def test_a_key_date_kind_is_written_as_its_lowercase_name() -> None:
    # Assert
    assert [kind.value for kind in KeyDateKind] == ["birthday", "anniversary", "other"]


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 1, 10), date(2026, 3, 14)),
        (date(2026, 3, 14), date(2026, 3, 14)),
        (date(2026, 3, 15), date(2027, 3, 14)),
        (date(2026, 12, 31), date(2027, 3, 14)),
    ],
    ids=["later-this-year", "on-the-day", "day-after", "year-end"],
)
def test_the_next_occurrence_is_the_first_matching_day_on_or_after_today(
    today: date, expected: date
) -> None:
    # Execute
    occurrence = a_key_date(month=3, day=14).next_occurrence(today)

    # Assert
    assert occurrence == expected


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2027, 1, 5), date(2027, 2, 28)),
        (date(2028, 1, 5), date(2028, 2, 29)),
        (date(2027, 3, 1), date(2028, 2, 29)),
        (date(2027, 2, 28), date(2027, 2, 28)),
    ],
    ids=["common-year", "leap-year", "after-the-common-year-date", "on-the-observed-day"],
)
def test_a_february_29_key_date_falls_on_february_28_in_a_common_year(
    today: date, expected: date
) -> None:
    # Execute
    occurrence = a_key_date(month=2, day=29, year=None).next_occurrence(today)

    # Assert
    assert occurrence == expected


def test_years_on_an_occurrence_counts_the_years_since_the_key_date_year() -> None:
    # Execute
    years = a_key_date(year=1990).years_on(date(2026, 3, 14))

    # Assert
    assert years == 36


def test_years_on_an_occurrence_is_unknown_when_the_key_date_has_no_year() -> None:
    # Execute
    years = a_key_date(year=None).years_on(date(2026, 3, 14))

    # Assert
    assert years is None
