import threading
from collections.abc import Callable

import pytest
from builders import a_capture
from capture_builders import FORCED_QUESTION, a_message, a_pipeline, an_agent_capture
from fakes.blocking_intake import BlockingIntake
from fakes.capture_filer import FakeCaptureFiler
from fakes.link_inspector import FakeLinkInspector
from fakes.memory_store import MemoryStore
from fakes.recording_intake import RecordingIntake
from threads import (
    OVERLAP_GRACE_SECONDS,
    WAIT_LIMIT_SECONDS,
    await_signal,
    run_in_thread,
    start,
    start_announcing,
)

from stash.capture import Duplicate, IsRequest
from stash.capture.serial import SerializedPipeline
from stash.domain import CaptureStatus

NO_WAIT_SECONDS = 0.2
Call = Callable[[SerializedPipeline], object]
CALLS: dict[str, Call] = {
    "handle": lambda pipeline: pipeline.handle(a_message()),
    "process": lambda pipeline: pipeline.process(a_capture()),
    "process_agent": lambda pipeline: pipeline.process_agent(an_agent_capture()),
    "retry_pending": lambda pipeline: pipeline.retry_pending(),
}


def test_receive_hands_the_message_to_the_inner_pipeline_and_returns_its_capture() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    capture = SerializedPipeline(inner).receive(a_message())

    # Assert
    assert (capture, inner.calls) == (inner.capture, ["receive"])


def test_process_hands_the_capture_to_the_inner_pipeline_and_returns_its_result() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    result = SerializedPipeline(inner).process(inner.capture)

    # Assert
    assert (result, inner.calls) == (inner.result, ["process"])


def test_handle_is_the_inner_pipelines_own_handle_not_a_receive_and_process_of_its_own() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    result = SerializedPipeline(inner).handle(a_message())

    # Assert
    assert (result, inner.calls) == (inner.result, ["handle"])


def test_retry_pending_is_the_inner_pipelines_own_retry_pending() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    results = SerializedPipeline(inner).retry_pending()

    # Assert
    assert (results, inner.calls) == ([inner.result], ["retry_pending"])


def test_process_agent_hands_the_capture_to_the_inner_pipeline_and_returns_its_result() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    result = SerializedPipeline(inner).process_agent(inner.capture)

    # Assert
    assert (result, inner.calls) == (inner.agent_result, ["process_agent"])


def test_receive_does_not_wait_for_a_call_that_is_holding_the_turn() -> None:
    # Setup
    inner = BlockingIntake()
    pipeline = SerializedPipeline(inner)
    start(lambda: pipeline.process(a_capture()))
    await_signal(inner.entered)

    # Execute
    capture = run_in_thread(lambda: pipeline.receive(a_message()))
    inner.release.set()

    # Assert
    assert capture == a_capture()


def test_handle_over_a_pipeline_whose_handle_calls_its_own_process_does_not_deadlock() -> None:
    # Setup
    store = MemoryStore()
    inner = a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler())
    pipeline = SerializedPipeline(inner)

    # Execute
    run_in_thread(lambda: pipeline.handle(a_message()))

    # Assert
    assert store.pending_captures() == []


def test_retry_pending_over_a_pipeline_whose_retry_calls_its_own_process_does_not_deadlock() -> (
    None
):
    # Setup
    store = MemoryStore()
    store.add_capture(a_capture())
    pipeline = SerializedPipeline(a_pipeline(store, FakeLinkInspector(), FakeCaptureFiler()))

    # Execute
    run_in_thread(pipeline.retry_pending)

    # Assert
    stored = store.get_capture(a_capture().id)
    assert stored is not None
    assert stored.status is CaptureStatus.FILED


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("handle", "handle"),
        ("process", "process"),
        ("retry_pending", "retry_pending"),
        ("handle", "retry_pending"),
        ("process", "handle"),
        ("retry_pending", "process"),
        ("process_agent", "process_agent"),
        ("process_agent", "process"),
        ("process", "process_agent"),
        ("handle", "process_agent"),
    ],
)
def test_two_calls_from_different_threads_never_run_inside_the_inner_pipeline_together(
    first: str, second: str
) -> None:
    # Setup
    inner = BlockingIntake()
    pipeline = SerializedPipeline(inner)
    contending = threading.Event()
    threads = [start(lambda: CALLS[first](pipeline))]
    await_signal(inner.entered)
    threads.append(start_announcing(contending, lambda: CALLS[second](pipeline)))
    await_signal(contending)
    inner.overlapped.wait(OVERLAP_GRACE_SECONDS)

    # Execute
    inner.release.set()
    for thread in threads:
        thread.join(WAIT_LIMIT_SECONDS)

    # Assert
    assert inner.max_inside == 1


def test_a_failing_call_gives_up_its_turn() -> None:
    # Setup
    inner = RecordingIntake()
    inner.fail_next = RuntimeError("boom")
    pipeline = SerializedPipeline(inner)
    with pytest.raises(RuntimeError, match="boom"):
        pipeline.handle(a_message())

    # Execute
    result = run_in_thread(lambda: pipeline.handle(a_message()))

    # Assert
    assert result == Duplicate()


def test_processing_a_capture_that_forces_a_request_returns_the_inner_pipelines_result() -> None:
    # Setup
    inner = RecordingIntake()

    # Execute
    result = SerializedPipeline(inner).process(a_capture(text=FORCED_QUESTION))

    # Assert
    assert (result, inner.calls) == (inner.result, ["process"])


def test_processing_a_forcing_capture_does_not_wait_for_a_call_holding_the_turn() -> None:
    # Setup
    inner = BlockingIntake()
    pipeline = SerializedPipeline(inner)
    start(lambda: pipeline.process(a_capture()))
    await_signal(inner.entered)
    forced = a_capture(text=FORCED_QUESTION)

    # Execute
    result = run_in_thread(lambda: pipeline.process(forced), timeout=NO_WAIT_SECONDS)
    inner.release.set()

    # Assert
    assert result == IsRequest(forced.with_status(CaptureStatus.REQUEST))


def test_processing_an_agent_capture_starting_with_a_question_mark_waits_for_the_turn() -> None:
    # Setup
    inner = BlockingIntake()
    pipeline = SerializedPipeline(inner)
    contending = threading.Event()
    threads = [start(lambda: pipeline.process(a_capture()))]
    await_signal(inner.entered)
    threads.append(
        start_announcing(
            contending, lambda: pipeline.process(an_agent_capture(text=FORCED_QUESTION))
        )
    )
    await_signal(contending)
    inner.overlapped.wait(OVERLAP_GRACE_SECONDS)

    # Execute
    inner.release.set()
    for thread in threads:
        thread.join(WAIT_LIMIT_SECONDS)

    # Assert
    assert inner.max_inside == 1
