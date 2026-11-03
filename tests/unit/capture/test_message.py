import pytest
from builders import BASE, NAIVE, a_source

from stash.capture import IncomingMessage


def test_an_incoming_message_with_a_naive_received_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="received_at must be timezone-aware"):
        IncomingMessage(a_source(), "hello", (), NAIVE)


def test_an_incoming_message_given_a_bare_string_of_media_paths_raises_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="media_paths must be a collection of strings"):
        IncomingMessage(a_source(), "", "photo.jpg", BASE)  # type: ignore[arg-type]


def test_an_incoming_message_ignores_later_changes_to_the_media_list_it_was_built_from() -> None:
    # Setup
    paths = ["media/a.jpg"]
    message = IncomingMessage(a_source(), "", paths, BASE)  # type: ignore[arg-type]

    # Execute
    paths.append("media/b.jpg")

    # Assert
    assert message.media_paths == ("media/a.jpg",)


@pytest.mark.parametrize(
    ("path", "problem"),
    [
        ("", "must not be blank"),
        ("media/a\x00.jpg", "NUL character"),
        ("https://evil.example/a.jpg", "must not be a URL"),
        ("../secret.jpg", "'..' segment"),
    ],
)
def test_an_incoming_message_refuses_an_unsafe_media_path(path: str, problem: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=problem):
        IncomingMessage(a_source(), "", ("media/a.jpg", path), BASE)


def test_an_absolute_gateway_cache_path_is_accepted() -> None:
    # Setup
    path = "/home/owner/.hermes/cache/images/img_ab12.jpg"

    # Execute
    message = IncomingMessage(a_source(), "", (path,), BASE)

    # Assert
    assert message.media_paths == (path,)
