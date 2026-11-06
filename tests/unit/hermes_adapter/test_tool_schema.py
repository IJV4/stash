from stash.hermes_adapter.tool_schema import owners_data, tool_schema

SUBJECT = "Notes"
PROPERTIES = {"item_id": {"type": "string"}}


def test_a_tool_schema_carries_the_tool_name() -> None:
    # Execute
    schema = tool_schema("stash_x", "Does x.", PROPERTIES, ["item_id"], subject=SUBJECT)

    # Assert
    assert schema["name"] == "stash_x"


def test_a_tool_schema_description_ends_with_the_owners_data_sentence_for_its_subject() -> None:
    # Execute
    schema = tool_schema("stash_x", "Does x.", PROPERTIES, ["item_id"], subject=SUBJECT)

    # Assert
    assert schema["description"] == f"Does x. {owners_data(SUBJECT)}"


def test_a_tool_schema_describes_an_object_of_the_given_properties() -> None:
    # Execute
    schema = tool_schema("stash_x", "Does x.", PROPERTIES, ["item_id"], subject=SUBJECT)

    # Assert
    assert (schema["parameters"]["type"], schema["parameters"]["properties"]) == (
        "object",
        PROPERTIES,
    )


def test_a_tool_schema_lists_the_required_parameters() -> None:
    # Execute
    schema = tool_schema("stash_x", "Does x.", PROPERTIES, ["item_id"], subject=SUBJECT)

    # Assert
    assert schema["parameters"]["required"] == ["item_id"]


def test_a_tool_schema_without_required_parameters_has_no_required_key() -> None:
    # Execute
    schema = tool_schema("stash_x", "Does x.", PROPERTIES, [], subject=SUBJECT)

    # Assert
    assert "required" not in schema["parameters"]
