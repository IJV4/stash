import io

from builders import a_capture, an_item
from fakes.pending_intake import PendingIntake
from stash.cli.commands import retry

from stash.capture import CaptureIntake, Deferred, Filed


def retried(intake: CaptureIntake) -> tuple[int, str]:
    out = io.StringIO()
    return retry(intake, out), out.getvalue()


def test_retry_prints_nothing_pending_when_no_capture_is_pending() -> None:
    # Execute
    result = retried(PendingIntake())

    # Assert
    assert result == (0, "Nothing pending.\n")


def test_retry_prints_one_line_for_each_processed_capture() -> None:
    # Setup
    intake = PendingIntake(
        [
            Filed(an_item(title="Ramen in Shibuya"), unsure=False),
            Deferred(a_capture(text="Dune by Frank Herbert"), "ai_unavailable"),
        ]
    )

    # Execute
    result = retried(intake)

    # Assert
    assert result == (
        0,
        "filed — Places · Ramen in Shibuya · Inbox\n"
        "deferred (ai_unavailable) — Dune by Frank Herbert\n",
    )


def test_retry_asks_the_pipeline_to_retry_its_pending_captures() -> None:
    # Setup
    intake = PendingIntake()

    # Execute
    retried(intake)

    # Assert
    assert intake.calls == ["retry_pending"]
