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
