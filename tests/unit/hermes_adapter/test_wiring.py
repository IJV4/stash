import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime

from app_builders import NOON, an_app, stored
from builders import an_item, stored_completion
from capture_builders import a_filing_answer, sequential_ids
from capture_rig import build_rig
from fakes.memory_store import MemoryStore
from fakes.pausing_scheduler import PausingScheduler
from fakes.pending_intake import PendingIntake
from fakes.recording_outbox import RecordingOutbox
from fakes.scripted_steps import ScriptedSteps
from hermes_events import OWNER_ID, an_event
from hermes_rig import app_over, instant_bursts

from stash.app import StashApp
from stash.capture import IncomingMessage, confirmation
from stash.domain import Stage
from stash.hermes_adapter.commands import GpuCommand, LibraryCommand, ListCommand, RetryCommand
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.wiring import build_commands, build_intake, build_scheduler, build_tools

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


def test_the_commands_are_list_gpu_retry_and_library() -> None:
    # Execute
    commands = build_commands(an_app())

    # Assert
    assert {name: type(command) for name, command in commands.items()} == {
        "list": ListCommand,
        "gpu": GpuCommand,
        "retry": RetryCommand,
        "library": LibraryCommand,
    }


def handler_named(app: StashApp, name: str) -> Callable[..., str]:
    return next(spec.handler for spec in build_tools(app) if spec.schema["name"] == name)


def test_the_tools_are_search_list_and_the_seven_lifecycle_tools() -> None:
    # Execute
    specs = build_tools(an_app())

    # Assert
    assert [spec.schema["name"] for spec in specs] == [
        "stash_search",
        "stash_list",
        "stash_get",
        "stash_complete",
        "stash_annotate",
        "stash_set_stage",
        "stash_keep",
        "stash_group",
        "stash_library",
    ]


def test_the_lifecycle_tools_act_on_the_lifecycle_of_the_app() -> None:
    # Setup
    store = stored(an_item(id="w1", capture_id="c1", stage=Stage.WANT_TO))
    complete = handler_named(an_app(store=store), "stash_complete")

    # Execute
    complete({"item_id": "w1", "rating": 3})

    # Assert
    assert [outcome.rating for outcome in store.outcomes_for("w1")] == [3]


def test_the_search_and_list_tools_read_the_store_of_the_app() -> None:
    # Setup
    store = stored(an_item(id="w1", capture_id="c1", title="Ramen"))
    search = handler_named(an_app(store=store), "stash_search")

    # Execute
    answer = search({"query": "ramen"})

    # Assert
    assert json.loads(answer)["items"][0]["id"] == "w1"


def test_the_library_command_lists_the_kept_items_of_the_app_lifecycle() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "k1", kept=True, title="Dune")
    command = build_commands(an_app(store=store))["library"]

    # Execute
    text = asyncio.run(command.run(""))

    # Assert
    assert text == "📚 Places: Dune · ⭐4"
