from collections.abc import Mapping
from typing import Any, cast

import pytest

from stash.suggestions.schema import SCHEMA_NAME, SUGGESTIONS_SCHEMA


def pick_item() -> Mapping[str, Any]:
    picks = cast(
        Mapping[str, Any], cast(Mapping[str, Any], SUGGESTIONS_SCHEMA["properties"])["picks"]
    )
    return cast(Mapping[str, Any], picks["items"])


def test_the_schema_is_named_suggestions() -> None:
    # Assert
    assert SCHEMA_NAME == "suggestions"


def test_the_schema_is_an_object_with_a_required_picks_array() -> None:
    # Execute
    schema = SUGGESTIONS_SCHEMA

    # Assert
    assert (schema["type"], schema["required"]) == ("object", ("picks",))


def test_the_schema_refuses_additional_top_level_properties() -> None:
    # Assert
    assert SUGGESTIONS_SCHEMA["additionalProperties"] is False


def test_picks_is_an_array() -> None:
    # Setup
    properties = cast(Mapping[str, Any], SUGGESTIONS_SCHEMA["properties"])

    # Execute
    picks = properties["picks"]

    # Assert
    assert picks["type"] == "array"


def test_each_pick_requires_an_item_id_and_a_reason() -> None:
    # Assert
    assert pick_item()["required"] == ("item_id", "reason")


def test_each_pick_refuses_additional_properties() -> None:
    # Assert
    assert pick_item()["additionalProperties"] is False


def test_an_item_id_and_a_reason_are_strings() -> None:
    # Execute
    properties = pick_item()["properties"]

    # Assert
    assert (properties["item_id"], properties["reason"]) == ({"type": "string"}, {"type": "string"})


def test_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, SUGGESTIONS_SCHEMA)["type"] = "array"


def test_a_nested_part_of_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, pick_item()["properties"])["extra"] = {}
