import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from app_builders import NOON, an_app
from capture_builders import sequential_ids
from config_builders import a_nudge_config, a_stash_config
from fakes.pausing_scheduler import PausingScheduler
from fakes.pending_intake import PendingIntake
from fakes.recording_outbox import RecordingOutbox
from fakes.recording_sender import RecordingSender
from fakes.scripted_steps import ScriptedSteps
from hermes_events import OWNER_ID, an_event
from ticker_rig import run_until

from stash.capture import IncomingMessage
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.wiring import (
    build_intake,
    build_ticker,
)

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


def test_the_ticker_pauses_the_tick_interval_the_app_is_configured_with() -> None:
    # Setup
    config = a_stash_config(nudges=a_nudge_config(tick_seconds=17))
    scheduler = PausingScheduler()
    ticker = build_ticker(an_app(config=config), RecordingSender(), OWNER_ID, scheduler=scheduler)

    # Execute
    asyncio.run(run_until(ticker, lambda: scheduler.requested))

    # Assert
    assert scheduler.requested[0] == 17.0
