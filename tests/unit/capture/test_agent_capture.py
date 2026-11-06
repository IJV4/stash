import logging

import pytest
from agent_capture_rig import a_filing_intake, an_agent_capture_over, build_agent_rig
from builders import BASE
from capture_builders import SAMPLE_TEXT, sequential_ids
from fakes.capture_filer import FakeCaptureFiler
from fakes.recording_intake import RecordingIntake
from log_records import recording_logs

from stash.capture import Deferred, Filed
from stash.capture.agent import AgentCaptureError
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.domain import CaptureStatus, SourceRef
from stash.llm import LlmUnavailable

NOTE = "recommended by Sam"
AGENT_LOGGER = "stash.capture.agent"


def test_filing_returns_the_filed_item() -> None:
    # Setup
    rig = build_agent_rig()

    # Execute
    result = rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert result == Filed(rig.store.list_items()[0], unsure=False)


def test_filing_marks_the_raw_capture_filed() -> None:
    # Setup
    rig = build_agent_rig()

    # Execute
    result = rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert isinstance(result, Filed)
    stored = rig.store.get_capture(result.item.capture_id)
    assert stored is not None and stored.status is CaptureStatus.FILED


def test_the_raw_capture_carries_an_agent_source() -> None:
    # Setup
    rig = build_agent_rig()

    # Execute
    result = rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert isinstance(result, Filed)
    stored = rig.store.get_capture(result.item.capture_id)
    assert stored is not None and stored.source.is_agent


def test_the_raw_capture_carries_a_fresh_message_id_per_call() -> None:
    # Setup
    rig = build_agent_rig()

    # Execute
    rig.agent.file(SAMPLE_TEXT)
    rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert len({item.capture_id for item in rig.store.list_items()}) == 2


def test_the_raw_capture_is_received_at_the_injected_clock_time() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.messages[0].received_at == BASE


def test_the_intake_receives_an_agent_source_built_from_a_new_id() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.messages[0].source == SourceRef.agent(sequential_ids()())


def test_the_intake_receives_the_text_alone_without_a_note() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.messages[0].text == SAMPLE_TEXT


def test_the_intake_receives_the_note_after_a_newline() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT, NOTE)

    # Assert
    assert intake.messages[0].text == f"{SAMPLE_TEXT}\n{NOTE}"


@pytest.mark.parametrize("note", ["", "   ", "\n"])
def test_a_blank_note_is_left_out(note: str) -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT, note)

    # Assert
    assert intake.messages[0].text == SAMPLE_TEXT


def test_the_intake_receives_no_media() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.messages[0].media_paths == ()


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_a_blank_text_is_refused(text: str) -> None:
    # Setup
    agent = an_agent_capture_over(RecordingIntake())

    # Execute / Assert
    with pytest.raises(ValueError, match="text must not be blank"):
        agent.file(text)


def test_a_blank_text_saves_nothing() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    with pytest.raises(ValueError, match="blank"):
        an_agent_capture_over(intake).file("  ", NOTE)

    # Assert
    assert intake.calls == []


def test_a_text_and_note_over_the_telegram_limit_are_refused() -> None:
    # Setup
    agent = an_agent_capture_over(RecordingIntake())
    text = "a" * (TELEGRAM_TEXT_LIMIT - 1)

    # Execute / Assert
    with pytest.raises(ValueError, match=str(TELEGRAM_TEXT_LIMIT)):
        agent.file(text, "bc")


def test_a_text_over_the_telegram_limit_saves_nothing() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    with pytest.raises(ValueError, match=str(TELEGRAM_TEXT_LIMIT)):
        an_agent_capture_over(intake).file("a" * (TELEGRAM_TEXT_LIMIT + 1))

    # Assert
    assert intake.calls == []


def test_a_text_and_note_of_exactly_the_telegram_limit_are_accepted() -> None:
    # Setup
    intake = a_filing_intake()
    text = "a" * (TELEGRAM_TEXT_LIMIT - 2)

    # Execute
    an_agent_capture_over(intake).file(text, "b")

    # Assert
    assert len(intake.messages[0].text) == TELEGRAM_TEXT_LIMIT


def test_a_blank_note_does_not_count_towards_the_limit() -> None:
    # Setup
    intake = a_filing_intake()
    text = "a" * TELEGRAM_TEXT_LIMIT

    # Execute
    an_agent_capture_over(intake).file(text, "   ")

    # Assert
    assert intake.messages[0].text == text


def test_an_unavailable_ai_defers_the_capture() -> None:
    # Setup
    rig = build_agent_rig(FakeCaptureFiler(error=LlmUnavailable("down")))

    # Execute
    result = rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert isinstance(result, Deferred) and result.reason == "ai_unavailable"


def test_an_unavailable_ai_leaves_the_raw_capture_pending_with_the_joined_text() -> None:
    # Setup
    rig = build_agent_rig(FakeCaptureFiler(error=LlmUnavailable("down")))

    # Execute
    rig.agent.file(SAMPLE_TEXT, NOTE)

    # Assert
    pending = rig.store.pending_captures()
    assert [(c.text, c.source.is_agent) for c in pending] == [(f"{SAMPLE_TEXT}\n{NOTE}", True)]


def test_a_message_the_intake_refuses_as_a_duplicate_is_an_error() -> None:
    # Setup
    intake = a_filing_intake()
    intake.duplicate = True

    # Execute / Assert
    with pytest.raises(AgentCaptureError, match="Duplicate"):
        an_agent_capture_over(intake).file(SAMPLE_TEXT)


def test_the_capture_is_received_before_it_is_processed() -> None:
    # Setup
    intake = a_filing_intake()

    # Execute
    an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.calls == ["receive", "process_agent"]


def test_an_unexpected_filing_failure_defers_the_capture() -> None:
    # Setup
    intake = a_filing_intake()
    intake.fail_next = RuntimeError("boom")

    # Execute
    result = an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert result == Deferred(intake.capture, "ai_unavailable")


def test_an_unexpected_filing_failure_leaves_the_raw_capture_pending() -> None:
    # Setup
    rig = build_agent_rig(FakeCaptureFiler(error=RuntimeError("boom")))

    # Execute
    rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert [capture.text for capture in rig.store.pending_captures()] == [SAMPLE_TEXT]


def test_an_unexpected_filing_failure_is_logged_with_the_capture_id() -> None:
    # Setup
    intake = a_filing_intake()
    intake.fail_next = RuntimeError("boom")

    # Execute
    with recording_logs(AGENT_LOGGER) as recorder:
        an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert recorder.entries() == [
        (logging.ERROR, f"agent capture {intake.capture.id} failed unexpectedly; left pending")
    ]


def test_a_failure_saving_the_raw_capture_is_raised() -> None:
    # Setup
    intake = a_filing_intake()
    intake.receive_error = RuntimeError("disk full")

    # Execute / Assert
    with pytest.raises(RuntimeError, match="disk full"):
        an_agent_capture_over(intake).file(SAMPLE_TEXT)


def test_a_failure_saving_the_raw_capture_does_not_start_processing() -> None:
    # Setup
    intake = a_filing_intake()
    intake.receive_error = RuntimeError("disk full")

    # Execute
    with pytest.raises(RuntimeError):
        an_agent_capture_over(intake).file(SAMPLE_TEXT)

    # Assert
    assert intake.calls == ["receive"]
