from collections.abc import Callable

from stash.app import StashApp
from stash.hermes_adapter.assistant import Assistant
from stash.hermes_adapter.bursts import Bursts
from stash.hermes_adapter.callbacks import FixCallbacks
from stash.hermes_adapter.commands import GpuCommand, LibraryCommand, ListCommand, RetryCommand
from stash.hermes_adapter.events import EventTranslator
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.lifecycle_tools import LifecycleTools
from stash.hermes_adapter.outbox import Outbox, ReplySender
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.scheduler import LoopScheduler, Scheduler
from stash.hermes_adapter.tool_spec import ToolSpec
from stash.hermes_adapter.tools import StashTools

Command = ListCommand | GpuCommand | RetryCommand | LibraryCommand


def build_scheduler(app: StashApp) -> LoopScheduler:
    return LoopScheduler(app.clock)


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
    return (*StashTools(app.store).specs(), *LifecycleTools(app.lifecycle).specs())


def build_commands(app: StashApp) -> dict[str, Command]:
    return {
        "list": ListCommand(app.store),
        "gpu": GpuCommand(app.gpu_switch, app.local_now),
        "retry": RetryCommand(app.pipeline),
        "library": LibraryCommand(app.lifecycle),
    }
