import logging

import pytest
from builders import a_capture, an_item
from capture_builders import FORCED_QUESTION
from hermes_events import ALLOW, CHAT_ID, SKIP, an_event
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


def test_a_processing_failure_is_skipped_by_hermes() -> None:
    # Setup
    harness = IntakeHarness(process_failure=RuntimeError("model exploded"))

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_failure_while_processing_a_forced_question_is_allowed_through_to_hermes() -> None:
    # Setup
    harness = IntakeHarness(process_failure=RuntimeError("disk full"))

    # Execute
    verdict = harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert verdict == ALLOW


def test_a_failure_while_processing_a_forced_question_is_logged_with_the_capture_id_only() -> None:
    # Setup
    harness = IntakeHarness(process_failure=RuntimeError("disk full"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert logs.entries() == [(logging.ERROR, f"processing capture {1:032x} failed")]


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


def test_a_forced_question_is_allowed_through_to_hermes() -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    verdict = harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert verdict == ALLOW


def test_a_forced_question_is_processed_with_its_text_unchanged() -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert [capture.text for capture in harness.steps.processed] == [FORCED_QUESTION]


def test_a_forced_question_is_saved_raw_before_it_is_processed() -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert harness.steps.calls == [("receive", FORCED_QUESTION), ("process", FORCED_QUESTION)]


def test_a_failed_raw_save_of_a_forced_question_processes_nothing() -> None:
    # Setup
    harness = IntakeHarness(receive_failure=RuntimeError("disk full"))

    # Execute
    harness.dispatch(an_event(text=FORCED_QUESTION, chat_id=CHAT_ID))

    # Assert
    assert harness.steps.processed == []
