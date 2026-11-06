from collections.abc import Mapping
from typing import Any, cast

import pytest

from stash.llm.schema import frozen_schema


def test_a_top_level_key_cannot_be_assigned() -> None:
    # Setup
    schema = frozen_schema({"type": "object"})

    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, schema)["type"] = "array"


def test_a_nested_mapping_cannot_be_assigned() -> None:
    # Setup
    schema = frozen_schema({"properties": {"title": {"type": "string"}}})

    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, schema["properties"])["title"] = {}


def test_a_list_becomes_a_tuple() -> None:
    # Execute
    schema = frozen_schema({"required": ["title", "date"]})

    # Assert
    assert schema["required"] == ("title", "date")


def test_a_mapping_inside_a_list_is_frozen() -> None:
    # Setup
    schema = frozen_schema({"anyOf": [{"type": "string"}]})

    # Execute / Assert
    with pytest.raises(TypeError):
        cast(Any, cast(tuple[Any, ...], schema["anyOf"])[0])["type"] = "null"


def test_scalars_are_left_as_they_are() -> None:
    # Execute
    schema = frozen_schema({"additionalProperties": False, "maxItems": 10})

    # Assert
    assert dict(schema) == {"additionalProperties": False, "maxItems": 10}


def test_changing_the_source_after_freezing_does_not_change_the_schema() -> None:
    # Setup
    source: dict[str, object] = {"properties": {"title": {"type": "string"}}}
    schema = frozen_schema(source)

    # Execute
    cast(dict[str, object], source["properties"])["extra"] = {}

    # Assert
    assert list(cast(Mapping[str, object], schema["properties"])) == ["title"]
