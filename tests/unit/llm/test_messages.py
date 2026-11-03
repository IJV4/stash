import dataclasses

import pytest

from stash.llm import ChatMessage, ImagePart, TextPart


def test_text_builds_a_message_with_a_single_text_part() -> None:
    # Execute
    message = ChatMessage.text("user", "hello")

    # Assert
    assert message.parts == (TextPart("hello"),)


def test_text_builds_a_message_with_the_given_role() -> None:
    # Execute
    message = ChatMessage.text("system", "be brief")

    # Assert
    assert message.role == "system"


def test_a_message_keeps_text_and_image_parts_in_order() -> None:
    # Setup
    parts = (TextPart("look"), ImagePart("data:image/png;base64,AAAA"))

    # Execute
    message = ChatMessage("user", parts)

    # Assert
    assert message.parts == parts


def test_a_message_ignores_later_changes_to_the_list_its_parts_came_from() -> None:
    # Setup
    parts = [TextPart("first")]
    message = ChatMessage("user", tuple(parts))

    # Execute
    parts.append(TextPart("second"))

    # Assert
    assert message.parts == (TextPart("first"),)


def test_a_message_built_from_a_list_of_parts_stores_a_tuple() -> None:
    # Execute
    message = ChatMessage("user", [TextPart("a")])  # type: ignore[arg-type]

    # Assert
    assert isinstance(message.parts, tuple)


def test_a_message_without_parts_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="at least one part"):
        ChatMessage("user", ())


def test_a_message_cannot_be_modified() -> None:
    # Setup
    message = ChatMessage.text("user", "hello")

    # Execute / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        message.role = "assistant"  # type: ignore[misc]


def test_a_text_part_cannot_be_modified() -> None:
    # Setup
    part = TextPart("hello")

    # Execute / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        part.text = "other"  # type: ignore[misc]


def test_an_image_part_cannot_be_modified() -> None:
    # Setup
    part = ImagePart("data:image/png;base64,AAAA")

    # Execute / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        part.data_url = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "data_url",
    ["http://example.test/a.png", "https://example.test/a.png", "", "file:///etc/passwd"],
    ids=["http", "https", "empty", "file"],
)
def test_an_image_part_rejects_anything_that_is_not_a_data_url(data_url: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="data:"):
        ImagePart(data_url)


def test_an_image_part_accepts_a_data_url() -> None:
    # Execute
    part = ImagePart("data:image/png;base64,AAAA")

    # Assert
    assert part.data_url == "data:image/png;base64,AAAA"
