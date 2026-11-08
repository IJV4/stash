import pytest
from agent_capture_rig import a_filing_intake, an_agent_capture_over, build_agent_rig
from capture_builders import SAMPLE_TEXT
from fakes.capture_filer import FakeCaptureFiler
from fakes.recording_intake import RecordingIntake

from stash.capture.agent import AgentCaptureError
from stash.capture.replies import TELEGRAM_TEXT_LIMIT

NOTE = "recommended by Sam"


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


def test_a_message_the_intake_refuses_as_a_duplicate_is_an_error() -> None:
    # Setup
    intake = a_filing_intake()
    intake.duplicate = True

    # Execute / Assert
    with pytest.raises(AgentCaptureError, match="Duplicate"):
        an_agent_capture_over(intake).file(SAMPLE_TEXT)


def test_an_unexpected_filing_failure_leaves_the_raw_capture_pending() -> None:
    # Setup
    rig = build_agent_rig(FakeCaptureFiler(error=RuntimeError("boom")))

    # Execute
    rig.agent.file(SAMPLE_TEXT)

    # Assert
    assert [capture.text for capture in rig.store.pending_captures()] == [SAMPLE_TEXT]


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
