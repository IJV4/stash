import pytest
from builders import NAIVE, a_capture

from stash.domain.capture import CaptureStatus, RawCapture, Route


def test_raw_capture_with_naive_received_at_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="received_at must be timezone-aware"):
        a_capture(received_at=NAIVE)


def test_raw_capture_media_paths_ignore_later_changes_to_the_list_they_were_built_from() -> None:
    # Setup
    paths = ["media/a.jpg"]
    capture = a_capture(media_paths=paths)

    # Execute
    paths.append("media/b.jpg")

    # Assert
    assert capture == a_capture(media_paths=("media/a.jpg",))


def test_with_status_returns_capture_carrying_the_new_status() -> None:
    # Setup
    capture = a_capture()

    # Execute
    filed = capture.with_status(CaptureStatus.FILED)

    # Assert
    assert filed.status is CaptureStatus.FILED


def test_with_status_leaves_the_original_capture_unchanged() -> None:
    # Setup
    capture = a_capture()

    # Execute
    capture.with_status(CaptureStatus.FILED)

    # Assert
    assert capture.status is CaptureStatus.PENDING


def test_with_status_keeps_every_other_field() -> None:
    # Setup
    capture = a_capture()

    # Execute
    filed = capture.with_status(CaptureStatus.FILED)

    # Assert
    assert filed == RawCapture(
        id=capture.id,
        source=capture.source,
        received_at=capture.received_at,
        text=capture.text,
        media_paths=capture.media_paths,
        status=CaptureStatus.FILED,
    )


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


def test_the_item_id_of_a_capture_is_the_capture_id() -> None:
    # Execute
    item_id = a_capture(id="c-42").item_id

    # Assert
    assert item_id == "c-42"


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


@pytest.mark.parametrize("path", ["media/a.jpg", "media/..hidden.jpg", "a..b/c.png", "photo.jpg"])
def test_raw_capture_accepts_a_plain_relative_media_path(path: str) -> None:
    # Execute
    capture = a_capture(media_paths=(path,))

    # Assert
    assert capture.media_paths == (path,)


@pytest.mark.parametrize(
    "capture_id", ["", "   ", "chat:42", "two words", "tab\there", "bell\x07", "x" * 41]
)
def test_raw_capture_refuses_an_id_that_cannot_travel_in_callback_data(capture_id: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="capture id"):
        a_capture(id=capture_id)


def test_raw_capture_accepts_an_id_of_the_maximum_length() -> None:
    # Execute
    capture = a_capture(id="x" * 40)

    # Assert
    assert capture.id == "x" * 40


def test_raw_capture_accepts_an_absolute_gateway_cache_path() -> None:
    # Execute
    capture = a_capture(media_paths=("/home/owner/.hermes/cache/images/img_ab12.jpg",))

    # Assert
    assert capture.media_paths == ("/home/owner/.hermes/cache/images/img_ab12.jpg",)


def test_raw_capture_refuses_forty_non_ascii_characters_because_telegram_counts_bytes() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="capture id"):
        a_capture(id="é" * 40)
