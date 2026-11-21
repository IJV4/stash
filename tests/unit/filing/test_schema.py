from collections.abc import Mapping
from typing import Any, cast

import pytest

from stash.domain import ItemType, Route, Stage
from stash.filing.schema import FILING_SCHEMA, SCHEMA_NAME

PROPERTIES = (
    "route",
    "item_type",
    "title",
    "stage",
    "details",
    "tags",
    "people",
    "date",
)


def properties() -> Mapping[str, Any]:
    return cast(Mapping[str, Any], FILING_SCHEMA["properties"])


def test_the_schema_is_named_filing() -> None:
    # Assert
    assert SCHEMA_NAME == "filing"


def test_the_schema_describes_an_object() -> None:
    # Assert
    assert FILING_SCHEMA["type"] == "object"


def test_the_route_enum_lists_every_route() -> None:
    # Assert
    assert properties()["route"]["enum"] == tuple(route.value for route in Route)


def test_the_item_type_enum_lists_every_item_type() -> None:
    # Assert
    assert properties()["item_type"]["enum"] == tuple(item_type.value for item_type in ItemType)


def test_the_stage_enum_offers_only_inbox_want_to_and_planned() -> None:
    # Assert
    assert properties()["stage"]["enum"] == (Stage.INBOX, Stage.WANT_TO, Stage.PLANNED)


@pytest.mark.parametrize("stage", [Stage.DOING, Stage.DONE, Stage.DROPPED])
def test_the_stage_enum_excludes_stages_the_ai_may_not_choose(stage: Stage) -> None:
    # Assert
    assert stage.value not in properties()["stage"]["enum"]


def test_every_property_is_required() -> None:
    # Assert
    assert sorted(cast(tuple[str, ...], FILING_SCHEMA["required"])) == sorted(PROPERTIES)


def test_the_schema_describes_exactly_the_filing_properties() -> None:
    # Assert
    assert sorted(properties()) == sorted(PROPERTIES)


def test_the_schema_refuses_additional_properties() -> None:
    # Assert
    assert FILING_SCHEMA["additionalProperties"] is False


def test_details_is_an_object_of_strings() -> None:
    # Assert
    assert properties()["details"] == {"type": "object", "additionalProperties": {"type": "string"}}


@pytest.mark.parametrize("name", ["tags", "people"])
def test_tags_and_people_are_arrays_of_strings(name: str) -> None:
    # Assert
    assert properties()[name] == {"type": "array", "items": {"type": "string"}}


def test_the_date_is_a_year_month_day_string_or_null() -> None:
    # Assert
    date = properties()["date"]
    assert (date["type"], date["pattern"]) == (
        ("string", "null"),
        "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
    )


def test_the_title_is_a_string() -> None:
    # Assert
    assert properties()["title"] == {"type": "string"}


def test_the_top_level_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        FILING_SCHEMA["type"] = "array"  # type: ignore[index]


def test_a_nested_level_of_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        properties()["title"]["type"] = "integer"


def test_the_properties_level_of_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        properties()["extra"] = {"type": "string"}  # type: ignore[index]


def test_the_required_list_cannot_be_appended_to() -> None:
    # Execute / Assert
    with pytest.raises(AttributeError):
        FILING_SCHEMA["required"].append("extra")  # type: ignore[attr-defined]


def test_an_enum_list_cannot_be_appended_to() -> None:
    # Execute / Assert
    with pytest.raises(AttributeError):
        properties()["route"]["enum"].append("extra")
