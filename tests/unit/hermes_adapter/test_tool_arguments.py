from datetime import date
from typing import Any

import pytest

from stash.domain import ItemType, Stage
from stash.hermes_adapter.tool_arguments import ToolArguments

NOT_OBJECTS = [None, "ramen", ["ramen"], 3]
UNSAFE_IDS = ["", "   ", "a:b", "two words", "é", "bell\x07", "x" * 41]
NOT_TEXT = [None, 5, 1.5, True, ["a"], {"a": "b"}]
NOT_BOOLEANS = ["true", 1, 0, 1.0, [True]]


def arguments(**values: Any) -> ToolArguments:
    return ToolArguments.of(values)


@pytest.mark.parametrize("raw", NOT_OBJECTS)
def test_arguments_that_are_not_an_object_are_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="arguments must be an object"):
        ToolArguments.of(raw)


def test_a_required_id_is_returned_as_given() -> None:
    # Execute
    item_id = arguments(item_id="b1").required_id("item_id")

    # Assert
    assert item_id == "b1"


def test_a_missing_required_id_is_refused_naming_it() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item_id must be text"):
        arguments().required_id("item_id")


@pytest.mark.parametrize("raw", [None, 5, 1.5, True, ["a"], {"a": "b"}])
def test_a_required_id_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item_id must be text"):
        arguments(item_id=raw).required_id("item_id")


@pytest.mark.parametrize("raw", UNSAFE_IDS)
def test_a_required_id_that_is_blank_or_not_wire_safe_is_refused(raw: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item_id must be"):
        arguments(item_id=raw).required_id("item_id")


def test_a_nullable_id_that_is_null_is_none() -> None:
    # Execute
    parent_id = arguments(parent_id=None).nullable_id("parent_id")

    # Assert
    assert parent_id is None


def test_a_nullable_id_is_returned_as_given() -> None:
    # Execute
    parent_id = arguments(parent_id="p1").nullable_id("parent_id")

    # Assert
    assert parent_id == "p1"


def test_a_missing_nullable_id_is_refused_rather_than_read_as_null() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="parent_id is required"):
        arguments().nullable_id("parent_id")


@pytest.mark.parametrize("raw", [5, 1.5, True, ["a"], "", "a:b", "x" * 41])
def test_a_nullable_id_that_is_neither_a_safe_id_nor_null_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="parent_id must be"):
        arguments(parent_id=raw).nullable_id("parent_id")


def test_required_text_is_returned_as_given() -> None:
    # Execute
    notes = arguments(notes="  Slow start  ").required_text("notes")

    # Assert
    assert notes == "  Slow start  "


@pytest.mark.parametrize("raw", NOT_TEXT)
def test_required_text_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be text"):
        arguments(notes=raw).required_text("notes")


def test_missing_required_text_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be text"):
        arguments().required_text("notes")


@pytest.mark.parametrize("values", [{}, {"notes": None}])
def test_absent_optional_text_is_empty(values: dict[str, Any]) -> None:
    # Execute
    notes = ToolArguments.of(values).optional_text("notes")

    # Assert
    assert notes == ""


def test_optional_text_is_returned_as_given() -> None:
    # Execute
    notes = arguments(notes="Slow start").optional_text("notes")

    # Assert
    assert notes == "Slow start"


@pytest.mark.parametrize("raw", [5, 1.5, True, ["a"]])
def test_optional_text_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="notes must be text"):
        arguments(notes=raw).optional_text("notes")


@pytest.mark.parametrize("values", [{}, {"reason": None}])
def test_an_absent_reason_is_none(values: dict[str, Any]) -> None:
    # Execute
    reason = ToolArguments.of(values).optional_reason()

    # Assert
    assert reason is None


def test_a_reason_is_returned_as_given() -> None:
    # Execute
    reason = arguments(reason="lost interest").optional_reason()

    # Assert
    assert reason == "lost interest"


@pytest.mark.parametrize("raw", [5, 1.5, True, ["a"]])
def test_a_reason_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="reason must be text"):
        arguments(reason=raw).optional_reason()


@pytest.mark.parametrize("values", [{}, {"rating": None}])
def test_an_absent_rating_is_none(values: dict[str, Any]) -> None:
    # Execute
    rating = ToolArguments.of(values).optional_rating()

    # Assert
    assert rating is None


def test_a_rating_is_returned_as_given() -> None:
    # Execute
    rating = arguments(rating=4).optional_rating()

    # Assert
    assert rating == 4


@pytest.mark.parametrize("raw", [True, False, 4.0, 4.5, "4", [4]])
def test_a_rating_that_is_a_bool_a_float_or_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="rating must be an integer"):
        arguments(rating=raw).optional_rating()


def test_a_rating_outside_the_scale_is_left_for_the_domain_to_refuse() -> None:
    # Execute
    rating = arguments(rating=9).optional_rating()

    # Assert
    assert rating == 9


@pytest.mark.parametrize("values", [{}, {"takeaways": None}])
def test_absent_takeaways_are_none_so_that_the_current_ones_can_be_kept(
    values: dict[str, Any],
) -> None:
    # Execute
    takeaways = ToolArguments.of(values).optional_takeaways()

    # Assert
    assert takeaways is None


def test_takeaways_are_returned_as_a_tuple_of_text() -> None:
    # Execute
    takeaways = arguments(takeaways=["Start small", "Salt early"]).optional_takeaways()

    # Assert
    assert takeaways == ("Start small", "Salt early")


def test_an_empty_list_of_takeaways_is_empty_not_absent() -> None:
    # Execute
    takeaways = arguments(takeaways=[]).optional_takeaways()

    # Assert
    assert takeaways == ()


@pytest.mark.parametrize("raw", ["Start small", 5, {"a": "b"}, True])
def test_takeaways_that_are_not_a_list_are_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="takeaways must be a list of text"):
        arguments(takeaways=raw).optional_takeaways()


@pytest.mark.parametrize("raw", [["ok", 5], [None], [["nested"]], ["ok", True]])
def test_takeaways_containing_something_other_than_text_are_refused(raw: list[Any]) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="takeaways must be a list of text"):
        arguments(takeaways=raw).optional_takeaways()


@pytest.mark.parametrize("flag", [True, False])
def test_a_required_bool_is_returned_as_given(flag: bool) -> None:
    # Execute
    kept = arguments(kept=flag).required_bool("kept")

    # Assert
    assert kept is flag


@pytest.mark.parametrize("raw", [None, *NOT_BOOLEANS])
def test_a_required_bool_that_is_not_a_bool_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="kept must be true or false"):
        arguments(kept=raw).required_bool("kept")


def test_a_missing_required_bool_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="kept must be true or false"):
        arguments().required_bool("kept")


@pytest.mark.parametrize("values", [{}, {"keep": None}])
def test_an_absent_optional_bool_is_none(values: dict[str, Any]) -> None:
    # Execute
    keep = ToolArguments.of(values).optional_bool("keep")

    # Assert
    assert keep is None


def test_an_optional_bool_is_returned_as_given() -> None:
    # Execute
    keep = arguments(keep=False).optional_bool("keep")

    # Assert
    assert keep is False


@pytest.mark.parametrize("raw", NOT_BOOLEANS)
def test_an_optional_bool_that_is_not_a_bool_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="keep must be true or false"):
        arguments(keep=raw).optional_bool("keep")


@pytest.mark.parametrize("values", [{}, {"completed_on": None}])
def test_an_absent_date_is_none(values: dict[str, Any]) -> None:
    # Execute
    completed_on = ToolArguments.of(values).optional_date("completed_on")

    # Assert
    assert completed_on is None


def test_a_date_is_read_as_year_month_day() -> None:
    # Execute
    completed_on = arguments(completed_on="2026-11-05").optional_date("completed_on")

    # Assert
    assert completed_on == date(2026, 11, 5)


@pytest.mark.parametrize("raw", [20261105, 1.5, True, ["2026-11-05"]])
def test_a_date_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="completed_on must be text"):
        arguments(completed_on=raw).optional_date("completed_on")


@pytest.mark.parametrize(
    "raw",
    ["yesterday", "", "2026-11-31", "20261105", "2026-W45-3", "2026-11-05T10:00", " 2026-11-05"],
)
def test_a_date_that_is_not_year_month_day_is_refused(raw: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="completed_on must be a date like 2026-11-05"):
        arguments(completed_on=raw).optional_date("completed_on")


def test_a_stage_is_read_by_value() -> None:
    # Execute
    stage = arguments(stage="dropped").stage()

    # Assert
    assert stage is Stage.DROPPED


def test_a_stage_is_read_in_any_case_and_spelling_of_want_to() -> None:
    # Execute
    stage = arguments(stage=" Want-To ").stage()

    # Assert
    assert stage is Stage.WANT_TO


@pytest.mark.parametrize("values", [{}, {"stage": None}, {"stage": 3}, {"stage": ["done"]}])
def test_a_missing_or_non_text_stage_is_refused(values: dict[str, Any]) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="stage must be text"):
        ToolArguments.of(values).stage()


def test_an_unknown_stage_is_refused_listing_the_valid_ones() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=r"unknown stage 'soonish' \(valid: inbox, want_to"):
        arguments(stage="soonish").stage()


@pytest.mark.parametrize("values", [{}, {"stage": None}])
def test_an_absent_optional_stage_is_none(values: dict[str, Any]) -> None:
    # Execute
    stage = ToolArguments.of(values).optional_stage()

    # Assert
    assert stage is None


def test_an_optional_stage_is_read_by_value() -> None:
    # Execute
    stage = arguments(stage="done").optional_stage()

    # Assert
    assert stage is Stage.DONE


@pytest.mark.parametrize("values", [{}, {"item_type": None}])
def test_an_absent_item_type_is_none(values: dict[str, Any]) -> None:
    # Execute
    item_type = ToolArguments.of(values).optional_item_type()

    # Assert
    assert item_type is None


def test_an_item_type_is_read_by_value() -> None:
    # Execute
    item_type = arguments(item_type="Book").optional_item_type()

    # Assert
    assert item_type is ItemType.BOOK


def test_an_unknown_item_type_is_refused_listing_the_valid_ones() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=r"unknown item_type 'spaceship' \(valid: place, recipe"):
        arguments(item_type="spaceship").optional_item_type()


@pytest.mark.parametrize("raw", [5, ["book"], True])
def test_an_item_type_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="item_type must be text"):
        arguments(item_type=raw).optional_item_type()


def test_an_absent_limit_is_the_default_page_size() -> None:
    # Execute
    limit = arguments().limit()

    # Assert
    assert limit == 20


def test_a_limit_is_returned_as_given() -> None:
    # Execute
    limit = arguments(limit=7).limit()

    # Assert
    assert limit == 7


@pytest.mark.parametrize("raw", [True, "5", 5.0, [5]])
def test_a_limit_that_is_not_an_integer_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="limit must be an integer"):
        arguments(limit=raw).limit()
