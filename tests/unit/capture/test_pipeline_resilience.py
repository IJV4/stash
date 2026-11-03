import logging

import pytest
from builders import BASE, LATER, minutes_after
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.failing_status_store import FailingStatusStore, StatusWriteFailed
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore
from log_records import recording_logs

from stash.capture import Filed, FixHandler
from stash.domain import CaptureStatus, ItemType

PIPELINE_LOGGER = "stash.capture.pipeline"


def two_pending_captures_where_the_first_fails() -> tuple[MemoryStore, FakeCaptureFiler, list[str]]:
    store = MemoryStore()
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    pipeline.receive(a_message("first", message_id="m1"))
    pipeline.receive(a_message("second", message_id="m2", received_at=minutes_after(1)))
    filer.fail_next = ValueError("boom")
    return store, filer, [capture.id for capture in store.pending_captures()]


def test_a_capture_that_raises_an_unexpected_error_does_not_stop_the_rest_of_the_batch() -> None:
    # Setup
    store, filer, _ = two_pending_captures_where_the_first_fails()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [isinstance(result, Filed) and result.item.title for result in results] == [
        "Filed by the fake"
    ]


def test_a_capture_that_raises_an_unexpected_error_stays_pending() -> None:
    # Setup
    store, filer, ids = two_pending_captures_where_the_first_fails()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    pipeline.retry_pending()

    # Assert
    assert [capture.id for capture in store.pending_captures()] == ids[:1]


def test_a_capture_that_raises_an_unexpected_error_is_logged_with_its_id_and_traceback() -> None:
    # Setup
    store, filer, ids = two_pending_captures_where_the_first_fails()
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    with recording_logs(PIPELINE_LOGGER) as recorder:
        pipeline.retry_pending()

    # Assert
    [record] = [r for r in recorder.records if r.levelno == logging.ERROR]
    assert (record.getMessage(), record.exc_info is not None) == (
        f"capture {ids[0]} failed unexpectedly; left pending",
        True,
    )


def failed_status_write_then_fixed_item() -> tuple[FailingStatusStore, FakeCaptureFiler]:
    store = FailingStatusStore()
    filer = FakeCaptureFiler()
    store.fail_next_status_write = True
    with pytest.raises(StatusWriteFailed):
        a_pipeline(store, FakeLinkInspector(), filer).handle(a_message())
    return store, filer


def test_a_retry_after_the_item_was_saved_but_the_status_write_failed_asks_the_filer_nothing() -> (
    None
):
    # Setup
    store, filer = failed_status_write_then_fixed_item()

    # Execute
    a_pipeline(store, FakeLinkInspector(), filer).retry_pending()

    # Assert
    assert len(filer.calls) == 1


def test_a_retry_after_such_a_failure_returns_the_existing_item_as_filed() -> None:
    # Setup
    store, filer = failed_status_write_then_fixed_item()
    saved = store.list_items()[0]

    # Execute
    results = a_pipeline(store, FakeLinkInspector(), filer, clock=lambda: LATER).retry_pending()

    # Assert
    assert results == [Filed(saved, unsure=False)]


def test_a_retry_after_such_a_failure_leaves_the_saved_item_untouched() -> None:
    # Setup
    store, filer = failed_status_write_then_fixed_item()
    saved = store.list_items()[0]

    # Execute
    a_pipeline(store, FakeLinkInspector(), filer, clock=lambda: LATER).retry_pending()

    # Assert
    assert store.get_item(saved.id) == saved


def test_a_retry_after_such_a_failure_marks_the_capture_filed() -> None:
    # Setup
    store, filer = failed_status_write_then_fixed_item()
    capture_id = store.list_items()[0].capture_id

    # Execute
    a_pipeline(store, FakeLinkInspector(), filer).retry_pending()

    # Assert
    capture = store.get_capture(capture_id)
    assert capture is not None and capture.status is CaptureStatus.FILED


def test_a_retry_does_not_overwrite_a_type_corrected_after_the_status_write_failed() -> None:
    # Setup
    store, filer = failed_status_write_then_fixed_item()
    saved = store.list_items()[0]
    FixHandler(store, lambda: BASE).apply(f"stash:T:{saved.id}:recipe")

    # Execute
    a_pipeline(store, FakeLinkInspector(), filer).retry_pending()

    # Assert
    corrected = store.get_item(saved.id)
    assert corrected is not None and corrected.item_type is ItemType.RECIPE
