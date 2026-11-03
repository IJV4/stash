import asyncio
import logging
import threading

import pytest
from builders import BASE
from capture_builders import a_filing_answer, sequential_ids
from capture_rig import CaptureRig, build_rig
from fakes.asked_assistant import AskedAssistant
from fakes.pausing_scheduler import PausingScheduler
from fakes.recording_sender import RecordingSender
from fakes.scripted_sender import ScriptedSender
from fakes.scripted_steps import ScriptedSteps
from hermes_events import STRANGER_ID, FakeEvent, an_event
from log_records import recording_logs

from stash.capture import Duplicate, ProcessResult, Reply, deferred
from stash.hermes_adapter.bursts import Bursts
from stash.hermes_adapter.events import Chat, EventTranslator
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.owners import Owners
from stash.llm import LlmError

LOGGER = "stash.hermes_adapter.intake"
OWNER_ID = "42"
CHAT_ID = "7001"
TEXT = "Ramen in Shibuya"
SKIP = {"action": "skip"}
ALLOW = {"action": "allow"}
APOLOGY_TEXT = "⚠️ I could not save that message — please send it again."


class UnreadableEvent:
    def __getattr__(self, name: str) -> object:
        raise RuntimeError(f"cannot read {name}")


class Harness:
    def __init__(
        self,
        rig: CaptureRig | None = None,
        receive_failure: Exception | None = None,
        process_failure: Exception | None = None,
        process_result: ProcessResult | None = None,
        sender: ReplySender | None = None,
    ) -> None:
        self.rig = rig or build_rig(a_filing_answer())
        self.steps = ScriptedSteps(
            self.rig.pipeline, receive_failure, process_failure, process_result
        )
        self.scheduler = PausingScheduler()
        self.assistant = AskedAssistant()
        self.reply_sender = ScriptedSender()
        self.apology_sender = sender or RecordingSender()
        self.intake = MessageIntake(
            EventTranslator(Owners.parse(OWNER_ID), lambda: BASE, sequential_ids()),
            self.steps,
            Bursts(lambda: self.rig.bursts, self.reply_sender, self.scheduler),
            self.assistant,
            self.apology_sender,
            self.scheduler,
        )

    def dispatch(self, event: FakeEvent | None = None) -> dict[str, str]:
        verdict = asyncio.run(self.intake.on_dispatch(event or an_event(chat_id=CHAT_ID)))
        self.scheduler.abandon()
        return verdict

    def dispatch_and_drain(self, event: FakeEvent | None = None) -> dict[str, str]:
        async def scenario() -> dict[str, str]:
            verdict = await self.intake.on_dispatch(event or an_event(chat_id=CHAT_ID))
            await self.scheduler.drain()
            return verdict

        return asyncio.run(scenario())


def test_an_owner_plain_text_message_is_skipped_by_hermes() -> None:
    # Setup
    harness = Harness()

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_the_message_is_received_on_a_worker_thread() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch()

    # Assert
    assert [t != threading.get_ident() for t in harness.steps.receive_threads] == [True]


def test_the_message_is_received_with_the_event_text() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch()

    # Assert
    assert [message.text for message in harness.steps.received] == [TEXT]


def test_a_message_is_processed_once_when_the_scheduler_runs() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert [capture.text for capture in harness.steps.processed] == [TEXT]


def test_processing_has_not_run_when_the_hook_returns() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch()

    # Assert
    assert harness.steps.processed == []


def test_processing_runs_on_a_worker_thread() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert [t != threading.get_ident() for t in harness.steps.process_threads] == [True]


def test_a_filed_result_is_confirmed_to_the_chat_after_the_burst_window() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert [chat_id for chat_id, _ in harness.reply_sender.sent] == [CHAT_ID]


def test_a_deferred_result_is_acknowledged_to_the_chat_after_the_burst_window() -> None:
    # Setup
    harness = Harness(rig=build_rig(error=LlmError("down")))

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert harness.reply_sender.sent == [(CHAT_ID, deferred("ai_unavailable"))]


def test_a_request_is_handed_to_the_assistant_with_the_chat() -> None:
    # Setup
    harness = Harness(rig=build_rig(a_filing_answer(route="request")))

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert harness.assistant.asked == [(TEXT, Chat(CHAT_ID, OWNER_ID))]


def test_a_request_is_not_confirmed_as_a_filed_item() -> None:
    # Setup
    harness = Harness(rig=build_rig(a_filing_answer(route="request")))

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert harness.reply_sender.sent == []


def test_a_duplicate_process_result_sends_and_asks_nothing() -> None:
    # Setup
    harness = Harness(process_result=Duplicate())

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert (harness.reply_sender.sent, harness.assistant.asked) == ([], [])


def test_a_message_received_twice_is_skipped_both_times() -> None:
    # Setup
    harness = Harness()
    harness.dispatch()

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_message_received_twice_is_processed_only_once() -> None:
    # Setup
    harness = Harness()
    harness.dispatch_and_drain()

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert [capture.text for capture in harness.steps.processed] == [TEXT]


def test_a_receive_failure_tells_the_chat_to_send_the_message_again() -> None:
    # Setup
    sender = RecordingSender()
    harness = Harness(receive_failure=RuntimeError("disk full"), sender=sender)

    # Execute
    harness.dispatch()

    # Assert
    assert sender.sent == [(CHAT_ID, Reply(APOLOGY_TEXT))]


def test_a_receive_failure_is_skipped_by_hermes() -> None:
    # Setup
    harness = Harness(receive_failure=RuntimeError("disk full"))

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_receive_failure_spawns_no_processing() -> None:
    # Setup
    harness = Harness(receive_failure=RuntimeError("disk full"))

    # Execute
    harness.dispatch()

    # Assert
    assert harness.scheduler.spawned == []


def test_a_receive_failure_is_logged_with_the_message_id_but_not_the_text() -> None:
    # Setup
    harness = Harness(receive_failure=RuntimeError("disk full"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.dispatch()

    # Assert
    assert logs.entries() == [(logging.ERROR, "could not save message m1 from chat 7001")]


def test_a_failure_to_send_the_apology_is_swallowed() -> None:
    # Setup
    harness = Harness(receive_failure=RuntimeError("disk full"), sender=ScriptedSender(failures=1))

    # Execute
    verdict = harness.dispatch()

    # Assert
    assert verdict == SKIP


def test_a_processing_failure_is_logged_with_the_capture_id_only() -> None:
    # Setup
    harness = Harness(process_failure=RuntimeError("model exploded"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.dispatch_and_drain()

    # Assert
    assert logs.entries() == [(logging.ERROR, f"processing capture {sequential_ids()()} failed")]


def test_a_processing_failure_sends_the_chat_nothing() -> None:
    # Setup
    harness = Harness(process_failure=RuntimeError("model exploded"))

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert (harness.reply_sender.sent, harness.assistant.asked) == ([], [])


def test_a_processing_failure_does_not_escape_the_spawned_task() -> None:
    # Setup
    harness = Harness(process_failure=RuntimeError("model exploded"))

    # Execute
    harness.dispatch_and_drain()

    # Assert
    assert harness.scheduler.failures == []


@pytest.mark.parametrize(
    "event",
    [an_event(text="/list"), an_event(user_id=STRANGER_ID)],
    ids=["command", "stranger"],
)
def test_commands_and_strangers_are_allowed_through_to_hermes(event: FakeEvent) -> None:
    # Setup
    harness = Harness()

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
    harness = Harness()

    # Execute
    harness.dispatch_and_drain(event)

    # Assert
    assert (harness.steps.received, harness.steps.processed) == ([], [])


def test_gateway_session_store_and_extra_keywords_are_accepted_and_ignored() -> None:
    # Setup
    harness = Harness()

    # Execute
    verdict = asyncio.run(
        harness.intake.on_dispatch(
            an_event(chat_id=CHAT_ID), gateway=object(), session_store=object(), platform="x"
        )
    )
    harness.scheduler.abandon()

    # Assert
    assert verdict == SKIP


def test_an_event_the_translator_cannot_read_is_allowed_through_to_hermes() -> None:
    # Setup
    harness = Harness()

    # Execute
    verdict = asyncio.run(harness.intake.on_dispatch(UnreadableEvent()))

    # Assert
    assert verdict == ALLOW


def test_an_event_the_translator_cannot_read_is_logged_without_any_message_text() -> None:
    # Setup
    harness = Harness()

    # Execute
    with recording_logs(LOGGER) as logs:
        asyncio.run(harness.intake.on_dispatch(UnreadableEvent()))

    # Assert
    assert logs.entries() == [(logging.ERROR, "could not read a gateway event")]
