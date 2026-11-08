import asyncio
import logging

import pytest
from fakes.scripted_sender import ScriptedSender
from hermes_events import ALLOW, SKIP, STRANGER_ID, FakeEvent, an_event
from intake_harness import IntakeHarness
from log_records import recording_logs

from stash.capture import Duplicate

LOGGER = "stash.hermes_adapter.intake"
APOLOGY_TEXT = "⚠️ I could not save that message — please send it again."


class UnreadableEvent:
    def __getattr__(self, name: str) -> object:
        raise RuntimeError(f"cannot read {name}")


def test_a_duplicate_process_result_sends_nothing() -> None:
    # Setup
    harness = IntakeHarness(process_result=Duplicate())

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert harness.reply_sender.sent == []


def test_a_failure_to_send_the_apology_is_swallowed() -> None:
    # Setup
    harness = IntakeHarness(
        receive_failure=RuntimeError("disk full"), apology_sender=ScriptedSender(failures=1)
    )

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


@pytest.mark.parametrize(
    "event",
    [an_event(text="/list"), an_event(user_id=STRANGER_ID)],
    ids=["command", "stranger"],
)
def test_commands_and_strangers_are_allowed_through_to_hermes(event: FakeEvent) -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    verdict = harness.dispatch(event)

    # Assert
    assert verdict == ALLOW


@pytest.mark.parametrize(
    "event",
    [an_event(text="/list"), an_event(user_id=STRANGER_ID)],
    ids=["command", "stranger"],
)
def test_commands_and_strangers_never_reach_the_intake_steps(event: FakeEvent) -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    harness.dispatch_and_drain(event)

    # Assert
    assert (harness.steps.received, harness.steps.processed) == ([], [])


def test_an_event_the_translator_cannot_read_is_allowed_through_to_hermes() -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    verdict = asyncio.run(harness.intake.on_dispatch(UnreadableEvent()))

    # Assert
    assert verdict == ALLOW


def test_an_event_the_translator_cannot_read_is_logged_without_any_message_text() -> None:
    # Setup
    harness = IntakeHarness()

    # Execute
    with recording_logs(LOGGER) as logs:
        asyncio.run(harness.intake.on_dispatch(UnreadableEvent()))

    # Assert
    assert logs.entries() == [(logging.ERROR, "could not read a gateway event")]
