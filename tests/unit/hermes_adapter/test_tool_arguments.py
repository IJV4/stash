from typing import Any

import pytest

from stash.domain import ItemType, KeyDateKind, Stage
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


@pytest.mark.parametrize("values", [{}, {"note": None}])
def test_an_absent_nullable_text_is_none(values: dict[str, Any]) -> None:
    # Execute
    note = ToolArguments.of(values).nullable_text("note")

    # Assert
    assert note is None


def test_a_nullable_text_is_returned_as_given() -> None:
    # Execute
    note = arguments(note="loved the ending").nullable_text("note")

    # Assert
    assert note == "loved the ending"


def test_a_nullable_text_keeps_an_empty_text_as_empty_not_absent() -> None:
    # Execute
    note = arguments(note="").nullable_text("note")

    # Assert
    assert note == ""


@pytest.mark.parametrize("raw", [5, 1.5, True, ["a"]])
def test_a_nullable_text_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="note must be text"):
        arguments(note=raw).nullable_text("note")


def test_a_required_int_is_returned_as_given() -> None:
    # Execute
    month = arguments(month=3).required_int("month")

    # Assert
    assert month == 3


@pytest.mark.parametrize("raw", [None, True, "3", 3.0, [3]])
def test_a_required_int_that_is_not_an_integer_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="month must be an integer"):
        arguments(month=raw).required_int("month")


@pytest.mark.parametrize("values", [{}, {"year": None}])
def test_an_absent_optional_year_is_none(values: dict[str, Any]) -> None:
    # Execute
    year = arguments(**values).optional_year()

    # Assert
    assert year is None


def test_an_optional_year_is_returned_as_given() -> None:
    # Execute
    year = arguments(year=1993).optional_year()

    # Assert
    assert year == 1993


@pytest.mark.parametrize("raw", [True, "1993", 1993.0, [1993]])
def test_an_optional_year_that_is_not_an_integer_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="year must be an integer"):
        arguments(year=raw).optional_year()


@pytest.mark.parametrize("values", [{}, {"aliases": None}])
def test_absent_optional_aliases_are_empty(values: dict[str, Any]) -> None:
    # Execute
    aliases = arguments(**values).optional_aliases()

    # Assert
    assert aliases == ()


@pytest.mark.parametrize("raw", [["Anita", "Ani"], ("Anita", "Ani")])
def test_optional_aliases_are_returned_as_a_tuple(raw: Any) -> None:
    # Execute
    aliases = arguments(aliases=raw).optional_aliases()

    # Assert
    assert aliases == ("Anita", "Ani")


@pytest.mark.parametrize("raw", ["Anita", 5, True, ["Anita", 5], ["Anita", None], [["Anita"]]])
def test_optional_aliases_that_are_not_a_list_of_text_are_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="aliases must be a list of text"):
        arguments(aliases=raw).optional_aliases()


def test_a_key_date_kind_is_read_by_value_ignoring_case() -> None:
    # Execute
    kind = arguments(kind="Anniversary").key_date_kind()

    # Assert
    assert kind is KeyDateKind.ANNIVERSARY


def test_an_unknown_key_date_kind_is_refused_listing_the_valid_ones() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=r"unknown kind 'holiday' .*birthday"):
        arguments(kind="holiday").key_date_kind()


@pytest.mark.parametrize("raw", [None, 5, True, ["birthday"]])
def test_a_key_date_kind_that_is_not_text_is_refused(raw: Any) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="kind must be text"):
        arguments(kind=raw).key_date_kind()
