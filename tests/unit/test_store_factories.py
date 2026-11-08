import tempfile
from pathlib import Path

from builders import a_capture
from fakes.store_factories import FreshStore, two_connections


def test_two_connections_see_the_same_database() -> None:
    # Setup
    capture = a_capture()

    with (
        tempfile.TemporaryDirectory() as directory,
        two_connections(Path(directory)) as (
            first,
            second,
        ),
    ):
        # Execute
        first.add_capture(capture)

        # Assert
        assert second.get_capture(capture.id) == capture


def test_two_fresh_stores_never_share_their_items() -> None:
    # Setup
    capture = a_capture()
    first, second = FreshStore(), FreshStore()

    # Execute
    first.add_capture(capture)

    # Assert
    assert second.get_capture(capture.id) is None
