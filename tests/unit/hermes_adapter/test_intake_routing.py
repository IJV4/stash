import logging

import pytest
from builders import a_capture, an_item
from hermes_events import ALLOW, SKIP
from intake_harness import IntakeHarness
from log_records import recording_logs

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult

LOGGER = "stash.hermes_adapter.intake"


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (Filed(an_item(), unsure=False), SKIP),
        (Filed(an_item(), unsure=True), SKIP),
        (Deferred(a_capture(), "ai_unavailable"), SKIP),
        (Deferred(a_capture(), "gpu_busy"), SKIP),
        (Duplicate(), SKIP),
        (IsRequest(a_capture()), ALLOW),
    ],
    ids=["filed", "filed-unsure", "ai-unavailable", "gpu-busy", "duplicate", "request"],
)
def test_the_verdict_for_each_processing_result(
    result: ProcessResult, expected: dict[str, str]
) -> None:
    # Setup
    harness = IntakeHarness(process_result=result)

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == expected


def test_a_failure_while_scheduling_the_confirmation_is_skipped_by_hermes() -> None:
    # Setup
    harness = IntakeHarness(burst_failure=RuntimeError("scheduler is closed"))

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_failure_while_scheduling_the_confirmation_is_logged_with_the_capture_id_only() -> None:
    # Setup
    harness = IntakeHarness(burst_failure=RuntimeError("scheduler is closed"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.dispatch()

    # Assert
    assert logs.entries() == [(logging.ERROR, f"processing capture {1:032x} failed")]


def test_a_processing_failure_whose_saved_reply_cannot_be_queued_is_still_skipped() -> None:
    # Setup
    harness = IntakeHarness(
        process_failure=RuntimeError("model exploded"),
        burst_failure=RuntimeError("scheduler is closed"),
    )

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_processing_failure_whose_saved_reply_cannot_be_queued_logs_both_failures() -> None:
    # Setup
    harness = IntakeHarness(
        process_failure=RuntimeError("model exploded"),
        burst_failure=RuntimeError("scheduler is closed"),
    )

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.dispatch()

    # Assert
    assert logs.entries() == [
        (logging.ERROR, f"processing capture {1:032x} failed"),
        (logging.ERROR, f"could not queue the saved reply for capture {1:032x}"),
    ]
