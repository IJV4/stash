import threading

import pytest
from threads import OverlapGate, await_signal, run_concurrently, run_in_thread, start

QUICK_TIMEOUT_SECONDS = 0.001


def test_run_in_thread_returns_the_workers_result() -> None:
    # Execute
    result = run_in_thread(lambda: 42)

    # Assert
    assert result == 42


def test_run_in_thread_re_raises_the_workers_exception_in_the_caller() -> None:
    # Setup
    def failing() -> int:
        raise ValueError("boom")

    # Execute / Assert
    with pytest.raises(ValueError, match="boom"):
        run_in_thread(failing)


def test_run_in_thread_raises_assertion_error_when_the_worker_does_not_finish() -> None:
    # Setup
    release = threading.Event()

    # Execute / Assert
    with pytest.raises(AssertionError, match="worker did not finish"):
        run_in_thread(release.wait, timeout=QUICK_TIMEOUT_SECONDS)
    release.set()


def test_run_concurrently_collects_the_exceptions_the_workers_raise() -> None:
    # Setup
    def failing(worker: int) -> None:
        raise ValueError(f"boom-{worker}")

    # Execute
    errors = run_concurrently(1, failing)

    # Assert
    assert [str(error) for error in errors] == ["boom-0"]


def test_run_concurrently_raises_assertion_error_when_a_worker_does_not_finish() -> None:
    # Setup
    release = threading.Event()

    # Execute / Assert
    with pytest.raises(AssertionError, match="worker did not finish"):
        run_concurrently(1, lambda worker: release.wait(), timeout=QUICK_TIMEOUT_SECONDS)
    release.set()


def test_a_gate_reports_when_two_holders_are_inside_at_once() -> None:
    # Setup
    gate = OverlapGate()
    first = start(gate.hold)
    await_signal(gate.entered)

    # Execute
    second = start(gate.hold)
    await_signal(gate.overlapped)
    gate.release.set()
    first.join()
    second.join()

    # Assert
    assert gate.max_inside == 2


def test_a_gate_counts_one_inside_for_holders_that_never_overlap() -> None:
    # Setup
    gate = OverlapGate()
    gate.release.set()

    # Execute
    gate.hold()
    gate.hold()

    # Assert
    assert gate.max_inside == 1


def test_a_gate_does_not_signal_overlap_for_holders_that_never_overlap() -> None:
    # Setup
    gate = OverlapGate()
    gate.release.set()

    # Execute
    gate.hold()
    gate.hold()

    # Assert
    assert not gate.overlapped.is_set()


def test_a_gate_signals_entered_when_a_holder_arrives() -> None:
    # Setup
    gate = OverlapGate()
    gate.release.set()

    # Execute
    gate.hold()

    # Assert
    assert gate.entered.is_set()
