import pytest
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.faulty_store import FaultyStore, StoreFault
from fakes.link_inspector import FakeLinkInspector

from stash.capture import Filed


def test_a_retry_after_a_crash_between_saving_the_item_and_the_status_makes_no_second_item() -> (
    None
):
    # Setup
    store = FaultyStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next("set_capture_status", StoreFault("status"))
    with pytest.raises(StoreFault):
        pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert len(store.list_items()) == 1


def test_a_retry_after_such_a_crash_marks_the_capture_filed() -> None:
    # Setup
    store = FaultyStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next("set_capture_status", StoreFault("status"))
    with pytest.raises(StoreFault):
        pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert store.pending_captures() == []


def test_a_crash_while_saving_the_item_leaves_the_capture_pending_for_a_retry() -> None:
    # Setup
    store = FaultyStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    store.fail_next("save_item", StoreFault("save"))
    with pytest.raises(StoreFault):
        pipeline.handle(a_message())

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [type(result) for result in results] == [Filed]
