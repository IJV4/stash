import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from app_builders import NOON, an_app
from capture_builders import a_filing_answer, sequential_ids
from capture_rig import build_rig
from fakes.pausing_scheduler import PausingScheduler
from fakes.pending_intake import PendingIntake
from fakes.recording_outbox import RecordingOutbox
from fakes.scripted_steps import ScriptedSteps
from hermes_events import OWNER_ID, an_event
from hermes_rig import app_over, instant_bursts

from stash.capture import IncomingMessage, confirmation
from stash.hermes_adapter.commands import GpuCommand, ListCommand, RetryCommand
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.wiring import build_commands, build_intake, build_scheduler

LATER = datetime(2026, 11, 3, 9, 30, tzinfo=UTC)


def dispatched_messages(
    steps: ScriptedSteps,
    now: datetime,
    *message_ids: str | None,
    new_id: Callable[[], str] | None = None,
) -> list[IncomingMessage]:
    app = an_app(pipeline=steps, clock=lambda: now)
    scheduler = PausingScheduler()
    intake = build_intake(
        app,
        Owners.parse(OWNER_ID),
        RecordingOutbox(),
        scheduler,
        new_id or sequential_ids(),
    )

    async def scenario() -> None:
        for message_id in message_ids:
            await intake.on_dispatch(an_event(message_id=message_id))
        await scheduler.drain()

    asyncio.run(scenario())
    return steps.received


def test_the_scheduler_tells_the_time_of_the_app_clock() -> None:
    # Setup
    app = an_app(clock=lambda: LATER)

    # Execute
    now = build_scheduler(app).now()

    # Assert
    assert now == LATER


def test_the_intake_stamps_messages_with_the_time_of_the_app_clock() -> None:
    # Execute
    [message] = dispatched_messages(ScriptedSteps(PendingIntake()), LATER, "m1")

    # Assert
    assert message.received_at == LATER


def test_the_intake_keeps_the_message_id_of_the_event() -> None:
    # Execute
    [message] = dispatched_messages(ScriptedSteps(PendingIntake()), NOON, "m1")

    # Assert
    assert message.source.message_id == "m1"


def test_events_without_a_message_id_get_the_ids_of_the_id_source_in_order() -> None:
    # Execute
    messages = dispatched_messages(
        ScriptedSteps(PendingIntake()), NOON, None, None, new_id=sequential_ids()
    )

    # Assert
    assert [message.source.message_id for message in messages] == [f"{1:032x}", f"{2:032x}"]


def test_the_id_source_is_not_used_for_events_that_carry_a_message_id() -> None:
    # Execute
    messages = dispatched_messages(
        ScriptedSteps(PendingIntake()), NOON, "m1", None, new_id=sequential_ids()
    )

    # Assert
    assert [message.source.message_id for message in messages] == ["m1", f"{1:032x}"]


def test_intakes_built_by_two_registrations_confirm_their_messages_separately() -> None:
    # Setup
    rig = build_rig(outcomes=[a_filing_answer(), a_filing_answer()])
    app = app_over(rig, burst_factory=instant_bursts)
    scheduler = PausingScheduler()
    outbox = RecordingOutbox()
    owners = Owners.parse(OWNER_ID)
    first_intake = build_intake(app, owners, outbox, scheduler, sequential_ids())
    second_intake = build_intake(app, owners, outbox, scheduler, sequential_ids())

    async def scenario() -> None:
        await first_intake.on_dispatch(an_event(message_id="m1"))
        await second_intake.on_dispatch(an_event(message_id="m2"))
        await scheduler.drain()

    # Execute
    asyncio.run(scenario())

    # Assert
    [first, second] = rig.store.list_items()
    assert outbox.sent_texts() == [
        confirmation(first, unsure=False).text,
        confirmation(second, unsure=False).text,
    ]


def test_the_commands_are_list_gpu_and_retry() -> None:
    # Execute
    commands = build_commands(an_app())

    # Assert
    assert {name: type(command) for name, command in commands.items()} == {
        "list": ListCommand,
        "gpu": GpuCommand,
        "retry": RetryCommand,
    }
