import pytest
from builders import NAIVE, a_capture

from stash.domain.capture import CaptureStatus, Route


def test_raw_capture_with_naive_received_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="received_at must be timezone-aware"):
        a_capture(received_at=NAIVE)


@pytest.mark.parametrize(
    ("member", "value"),
    [
        (Route.CAPTURE, "capture"),
        (Route.REQUEST, "request"),
        (Route.UNSURE, "unsure"),
        (CaptureStatus.PENDING, "pending"),
        (CaptureStatus.FILED, "filed"),
        (CaptureStatus.REQUEST, "request"),
    ],
)
def test_enum_member_serialises_to_its_stored_value(member: str, value: str) -> None:
    # Assert
    assert member == value


def test_raw_capture_media_paths_given_a_bare_string_raise_type_error() -> None:
    # Execute / Assert
    with pytest.raises(TypeError, match="media_paths must be a collection of strings"):
        a_capture(media_paths="photo.jpg")


@pytest.mark.parametrize(
    ("path", "problem"),
    [
        ("", "must not be blank"),
        ("   ", "must not be blank"),
        ("media/a\x00.jpg", "NUL character"),
        ("https://evil.example/a.jpg", "must not be a URL"),
        ("file:///etc/passwd", "must not be a URL"),
        ("../secret.jpg", "'..' segment"),
        ("media/../../secret.jpg", "'..' segment"),
        ("media\\..\\secret.jpg", "'..' segment"),
    ],
)
def test_raw_capture_refuses_an_unsafe_media_path(path: str, problem: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match=problem):
        a_capture(media_paths=("media/a.jpg", path))


@pytest.mark.parametrize(
    "capture_id", ["", "   ", "chat:42", "two words", "tab\there", "bell\x07", "x" * 41]
)
def test_raw_capture_refuses_an_id_that_cannot_travel_in_callback_data(capture_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="capture id"):
        a_capture(id=capture_id)


def test_raw_capture_refuses_forty_non_ascii_characters_because_telegram_counts_bytes() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="capture id"):
        a_capture(id="é" * 40)
