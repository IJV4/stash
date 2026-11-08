import pytest
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.failing_save_store import FailingSaveStore, SaveFailed
from fakes.failing_status_store import FailingStatusStore, StatusWriteFailed
from fakes.link_inspector import FakeLinkInspector

from stash.capture import Filed


def test_a_retry_after_a_crash_between_saving_the_item_and_the_status_makes_no_second_item() -> (
    None
):
    # Setup
    store = FailingStatusStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next_status_write = True
    with pytest.raises(StatusWriteFailed):
        pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert len(store.list_items()) == 1


def test_a_retry_after_such_a_crash_marks_the_capture_filed() -> None:
    # Setup
    store = FailingStatusStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next_status_write = True
    with pytest.raises(StatusWriteFailed):
        pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert store.pending_captures() == []


def test_a_crash_while_saving_the_item_leaves_the_capture_pending_for_a_retry() -> None:
    # Setup
    store = FailingSaveStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next_save = True
    with pytest.raises(SaveFailed):
        pipeline.handle(a_message())

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [type(result) for result in results] == [Filed]
