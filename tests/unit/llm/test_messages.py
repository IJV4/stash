import dataclasses

import pytest

from stash.llm import ChatMessage, ImagePart, TextPart


def test_a_message_without_parts_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="at least one part"):
        ChatMessage("user", ())


def test_a_text_part_cannot_be_modified() -> None:
    # Setup
    part = TextPart("hello")

    # Execute / Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        part.text = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    "data_url",
    ["http://example.test/a.png", "https://example.test/a.png", "", "file:///etc/passwd"],
    ids=["http", "https", "empty", "file"],
)
def test_an_image_part_rejects_anything_that_is_not_a_data_url(data_url: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="data:"):
        ImagePart(data_url)
