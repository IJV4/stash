import pytest
from builders import a_filing, minutes_after
from capture_builders import a_message, a_pipeline
from fakes.capture_filer import FakeCaptureFiler
from fakes.failing_save_store import FailingSaveStore, SaveFailed
from fakes.failing_status_store import FailingStatusStore, StatusWriteFailed
from fakes.link_inspector import FakeLinkInspector
from fakes.store_factories import FreshStore

from stash.capture import Deferred, Filed
from stash.capture.results import DeferralReason
from stash.domain import CaptureStatus
from stash.llm import LlmDeferred, LlmError, LlmUnavailable


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (LlmDeferred("GPU busy"), "gpu_busy"),
        (LlmUnavailable("down"), "ai_unavailable"),
        (LlmError("rejected key"), "ai_unavailable"),
        (LlmError("unknown model"), "ai_unavailable"),
        (LlmError("HTTP 401 unauthorized"), "ai_unavailable"),
        (LlmError("HTTP 403 forbidden"), "ai_unavailable"),
        (LlmError("HTTP 404 model not found"), "ai_unavailable"),
    ],
)
def test_an_llm_failure_defers_the_capture_with_the_matching_reason(
    error: LlmError, reason: DeferralReason
) -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler(error=error))

    # Execute
    result = pipeline.handle(a_message())

    # Assert
    assert result == Deferred(store.pending_captures()[0], reason)


@pytest.mark.parametrize(
    "error",
    [
        LlmDeferred("GPU busy"),
        LlmUnavailable("down"),
        LlmError("rejected key"),
        LlmError("unknown model"),
        LlmError("HTTP 404 model not found"),
    ],
)
def test_a_capture_deferred_by_any_llm_failure_stays_pending(error: LlmError) -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler(error=error))

    # Execute
    pipeline.handle(a_message())

    # Assert
    assert [capture.status for capture in store.pending_captures()] == [CaptureStatus.PENDING]


def test_a_deferred_capture_stays_pending() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(error=LlmUnavailable("down"))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(a_message())

    # Assert
    assert [capture.status for capture in store.pending_captures()] == [CaptureStatus.PENDING]


def test_a_deferred_capture_writes_no_item() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(error=LlmDeferred("GPU busy"))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)

    # Execute
    pipeline.handle(a_message())

    # Assert
    assert store.list_items() == []


def test_a_retry_after_the_filer_recovers_files_the_deferred_capture() -> None:
    # Setup
    filer = FakeCaptureFiler(error=LlmDeferred("GPU busy"))
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    pipeline.handle(a_message())
    filer.error = None

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [type(result) for result in results] == [Filed]


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


def test_retry_processes_every_pending_capture_oldest_first_even_when_each_is_deferred() -> None:
    # Setup
    store = FreshStore()
    filer = FakeCaptureFiler(error=LlmUnavailable("down"))
    pipeline = a_pipeline(store, FakeLinkInspector(), filer)
    for minute, name in [(2, "newest"), (0, "oldest"), (1, "middle")]:
        pipeline.receive(a_message(name, message_id=name, received_at=minutes_after(minute)))

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [result.capture.text for result in results if isinstance(result, Deferred)] == [
        "oldest",
        "middle",
        "newest",
    ]


def test_retry_files_the_pending_captures_and_returns_one_result_for_each() -> None:
    # Setup
    store = FreshStore()
    pipeline = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler(filing=a_filing()))
    pipeline.receive(a_message(message_id="m1"))
    pipeline.receive(a_message(message_id="m2", received_at=minutes_after(1)))

    # Execute
    results = pipeline.retry_pending()

    # Assert
    assert [isinstance(result, Filed) for result in results] == [True, True]


def test_retry_with_nothing_pending_returns_an_empty_list() -> None:
    # Setup
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), FakeCaptureFiler())

    # Execute / Assert
    assert pipeline.retry_pending() == []


def test_retry_does_not_touch_captures_that_are_already_filed() -> None:
    # Setup
    filer = FakeCaptureFiler()
    pipeline = a_pipeline(FreshStore(), FakeLinkInspector(), filer)
    pipeline.handle(a_message())

    # Execute
    pipeline.retry_pending()

    # Assert
    assert len(filer.calls) == 1


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
