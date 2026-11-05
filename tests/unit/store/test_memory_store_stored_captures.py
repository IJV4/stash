from builders import a_capture
from fakes.memory_store import MemoryStore

from stash.domain import CaptureStatus


def test_stored_captures_include_the_ones_that_are_no_longer_pending() -> None:
    # Setup
    store = MemoryStore()
    capture = a_capture()
    store.add_capture(capture)
    store.set_capture_status(capture.id, CaptureStatus.REQUEST)

    # Execute
    statuses = [stored.status for stored in store.stored_captures()]

    # Assert
    assert statuses == [CaptureStatus.REQUEST]
