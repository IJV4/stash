from collections.abc import Mapping
from typing import Any, cast

import pytest

from stash.planning.schema import SCHEMA_NAME, STEPS_SCHEMA


def step_item() -> Mapping[str, Any]:
    steps = cast(Mapping[str, Any], cast(Mapping[str, Any], STEPS_SCHEMA["properties"])["steps"])
    return cast(Mapping[str, Any], steps["items"])


def test_the_schema_is_named_prep_steps() -> None:
    # Execute
    name = SCHEMA_NAME

    # Assert
    assert name == "prep_steps"


def test_the_schema_is_an_object_with_a_required_steps_array() -> None:
    # Execute
    schema = STEPS_SCHEMA

    # Assert
    assert (schema["type"], schema["required"]) == ("object", ("steps",))


def test_the_schema_refuses_additional_top_level_properties() -> None:
    # Execute
    schema = STEPS_SCHEMA

    # Assert
    assert schema["additionalProperties"] is False


def test_steps_is_an_array() -> None:
    # Setup
    properties = cast(Mapping[str, Any], STEPS_SCHEMA["properties"])

    # Execute
    steps = properties["steps"]

    # Assert
    assert steps["type"] == "array"


def test_each_step_requires_a_text_and_lead_days() -> None:
    # Execute
    step = step_item()

    # Assert
    assert step["required"] == ("text", "lead_days")


def test_each_step_refuses_additional_properties() -> None:
    # Execute
    step = step_item()

    # Assert
    assert step["additionalProperties"] is False


def test_a_step_text_is_a_string_and_lead_days_an_integer() -> None:
    # Execute
    properties = step_item()["properties"]

    # Assert
    assert (properties["text"], properties["lead_days"]) == (
        {"type": "string"},
        {"type": "integer"},
    )


def test_the_schema_puts_no_numeric_bounds_on_lead_days() -> None:
    # Execute
    lead_days = step_item()["properties"]["lead_days"]

    # Assert
    assert set(lead_days) == {"type"}


def test_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, STEPS_SCHEMA)["type"] = "array"


def test_a_nested_part_of_the_schema_is_read_only() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, step_item()["properties"])["extra"] = {}
