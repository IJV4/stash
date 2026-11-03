from datetime import date

import pytest

from stash.domain import Filing, ItemType, Route, Stage
from stash.filing.parse import ISO_DATE, parse_filing
from stash.filing.schema import DATE_PATTERN

FALLBACK = "Ramen in Shibuya\nsecond line"
FALLBACK_TITLE = "Ramen in Shibuya"


def test_an_empty_answer_is_filed_as_other_inbox_unsure_titled_from_the_text() -> None:
    # Execute
    filing = parse_filing({}, FALLBACK)

    # Assert
    assert filing == Filing(
        route=Route.UNSURE,
        item_type=ItemType.OTHER,
        title=FALLBACK_TITLE,
        stage=Stage.INBOX,
        details={},
        tags=(),
        people=(),
        date=None,
    )


def test_a_known_route_is_kept() -> None:
    # Assert
    assert parse_filing({"route": "request"}, FALLBACK).route is Route.REQUEST


def test_an_unknown_route_becomes_unsure() -> None:
    # Assert
    assert parse_filing({"route": "delete-everything"}, FALLBACK).route is Route.UNSURE


def test_a_known_item_type_is_kept() -> None:
    # Assert
    assert parse_filing({"item_type": "recipe"}, FALLBACK).item_type is ItemType.RECIPE


def test_an_unknown_item_type_becomes_other() -> None:
    # Assert
    assert parse_filing({"item_type": "spaceship"}, FALLBACK).item_type is ItemType.OTHER


@pytest.mark.parametrize("stage", [Stage.INBOX, Stage.WANT_TO])
def test_a_fileable_stage_is_kept(stage: Stage) -> None:
    # Assert
    assert parse_filing({"stage": stage.value}, FALLBACK).stage is stage


@pytest.mark.parametrize("stage", ["done", "doing", "dropped", "archived"])
def test_a_forbidden_or_unknown_stage_becomes_inbox(stage: str) -> None:
    # Assert
    assert parse_filing({"stage": stage}, FALLBACK).stage is Stage.INBOX


def test_a_title_from_the_answer_is_used() -> None:
    # Assert
    assert parse_filing({"title": "Ichiran ramen"}, FALLBACK).title == "Ichiran ramen"


@pytest.mark.parametrize("title", ["", "   \n\t", None])
def test_a_missing_or_blank_title_is_taken_from_the_text(title: str | None) -> None:
    # Assert
    assert parse_filing({"title": title}, FALLBACK).title == FALLBACK_TITLE


def test_a_title_has_its_whitespace_collapsed() -> None:
    # Assert
    assert parse_filing({"title": "  Ichiran \t ramen  "}, FALLBACK).title == "Ichiran ramen"


def test_a_title_of_300_characters_is_clipped_to_120() -> None:
    # Assert
    assert len(parse_filing({"title": "x" * 300}, FALLBACK).title) == 120


def test_a_title_of_only_the_first_line_is_kept() -> None:
    # Assert
    assert parse_filing({"title": "First\nSecond"}, FALLBACK).title == "First"


def test_a_planned_stage_with_a_valid_date_is_planned_on_that_date() -> None:
    # Execute
    filing = parse_filing({"stage": "planned", "date": "2026-11-14"}, FALLBACK)

    # Assert
    assert (filing.stage, filing.date) == (Stage.PLANNED, date(2026, 11, 14))


@pytest.mark.parametrize(
    "bad_date",
    [
        "next week",
        "2026-13-45",
        "20261114",
        "2026-11-14\n",
        "\u0662\u0660\u0662\u0666-\u0661\u0661-\u0661\u0664",
        "",
        None,
        20261114,
    ],
)
def test_a_planned_stage_without_a_valid_date_becomes_want_to(bad_date: object) -> None:
    # Execute
    filing = parse_filing({"stage": "planned", "date": bad_date}, FALLBACK)

    # Assert
    assert (filing.stage, filing.date) == (Stage.WANT_TO, None)


def test_a_planned_stage_without_a_date_key_becomes_want_to() -> None:
    # Assert
    assert parse_filing({"stage": "planned"}, FALLBACK).stage is Stage.WANT_TO


def test_a_valid_date_on_an_unplanned_item_is_kept() -> None:
    # Assert
    assert parse_filing({"stage": "want_to", "date": "2026-11-14"}, FALLBACK).date == date(
        2026, 11, 14
    )


@pytest.mark.parametrize("bad_date", ["2026-13-45", "next week", "20261114", "2026-11-14\n"])
def test_an_invalid_date_on_an_unplanned_item_is_dropped(bad_date: str) -> None:
    # Assert
    assert parse_filing({"stage": "want_to", "date": bad_date}, FALLBACK).date is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("route", 3),
        ("route", ["capture"]),
        ("item_type", 3),
        ("item_type", None),
        ("item_type", {"place": 1}),
        ("title", 3),
        ("title", ["Ramen"]),
        ("stage", True),
        ("stage", ["inbox"]),
        ("details", "city=Tokyo"),
        ("details", ["city"]),
        ("tags", "ramen"),
        ("tags", 3),
        ("people", "Ana"),
        ("people", {"Ana": "friend"}),
        ("date", 1.5),
        ("date", ["2026-11-14"]),
    ],
)
def test_a_wrongly_typed_value_is_treated_as_missing(field: str, value: object) -> None:
    # Assert
    assert parse_filing({field: value}, FALLBACK) == parse_filing({}, FALLBACK)


def test_the_date_shape_the_parser_accepts_is_the_one_the_schema_advertises() -> None:
    # Execute / Assert
    assert ISO_DATE.pattern == DATE_PATTERN
