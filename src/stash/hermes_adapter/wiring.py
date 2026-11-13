from collections.abc import Callable

from stash.app import StashApp
from stash.hermes_adapter.assistant import Assistant
from stash.hermes_adapter.bursts import Bursts
from stash.hermes_adapter.callbacks import FixCallbacks
from stash.hermes_adapter.capture_tools import CaptureTools
from stash.hermes_adapter.commands import (
    FindCommand,
    GpuCommand,
    LibraryCommand,
    ListCommand,
    PeopleCommand,
    RetryCommand,
)
from stash.hermes_adapter.events import EventTranslator
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.library_file import LibraryFile
from stash.hermes_adapter.lifecycle_tools import LifecycleTools
from stash.hermes_adapter.outbox import Outbox, ReplySender
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.people_tools import PeopleTools
from stash.hermes_adapter.scheduler import LoopScheduler, Scheduler
from stash.hermes_adapter.step_tools import StepTools
from stash.hermes_adapter.suggest_command import SuggestCommand
from stash.hermes_adapter.suggest_tools import SuggestTools
from stash.hermes_adapter.ticker import Ticker
from stash.hermes_adapter.tool_spec import ToolSpec
from stash.hermes_adapter.tools import StashTools

Command = (
    FindCommand
    | ListCommand
    | GpuCommand
    | RetryCommand
    | LibraryCommand
    | SuggestCommand
    | PeopleCommand
)


def build_scheduler(app: StashApp) -> LoopScheduler:
    return LoopScheduler(app.clock)


def build_ticker(
    app: StashApp, sender: ReplySender, owner_chat: str, scheduler: Scheduler | None = None
) -> Ticker:
    return Ticker(
        app.nudge_delivery,
        app.proposal_delivery,
        app.retry_delivery,
        sender,
        owner_chat,
        scheduler or build_scheduler(app),
        app.config.nudges.tick_seconds,
    )


def build_intake(
    app: StashApp,
    owners: Owners,
    sender: ReplySender,
    scheduler: Scheduler,
    new_id: Callable[[], str],
) -> MessageIntake:
    return MessageIntake(
        EventTranslator(owners, app.clock, new_id),
        app.pipeline,
        Bursts(app.burst_factory, sender, scheduler),
        sender,
    )


def build_callbacks(
    app: StashApp, owners: Owners, outbox: Outbox, assistant: Assistant
) -> FixCallbacks:
    return FixCallbacks(app.fixes, owners, outbox, assistant)


def build_tools(app: StashApp) -> tuple[ToolSpec, ...]:
    return (
        *StashTools(app.store).specs(),
        *LifecycleTools(app.lifecycle).specs(),
        *CaptureTools(app.agent_capture).specs(),
        *StepTools(app.planning).specs(),
        *SuggestTools(app.suggestions).specs(),
        *PeopleTools(app.people, app.today).specs(),
    )


def build_commands(app: StashApp, outbox: Outbox, owner_chat: str | None) -> dict[str, Command]:
    library_file = LibraryFile(app, outbox, owner_chat)
    return {
        "list": ListCommand(app.store),
        "find": FindCommand(app.store),
        "gpu": GpuCommand(app.gpu_switch, app.local_now),
        "retry": RetryCommand(app.pipeline),
        "library": LibraryCommand(app.lifecycle, library_file.send),
        "suggest": SuggestCommand(app.suggestions),
        "people": PeopleCommand(app.people, app.today),
    }
