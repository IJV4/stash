import asyncio
import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_builders import an_app
from capture_builders import SAMPLE_TEXT, sequential_ids
from capture_rig import CaptureRig, build_rig
from config_builders import a_stash_config
from fakes.hermes_ctx import FakeHermesContext
from fakes.pausing_scheduler import PausingScheduler
from fakes.recording_assistant import RecordingAssistant
from fakes.recording_outbox import RecordingOutbox
from fakes.store_factories import FreshStore
from hermes_ctx_builders import a_hermes_context
from hermes_events import OWNER_ID, FakeEvent, an_event

from stash.app import StashApp
from stash.capture import BurstCoalescer, CaptureIntake, Reply, SerializedPipeline
from stash.config import StashConfig
from stash.domain import CaptureStatus
from stash.enrich.links import LinkInfo
from stash.hermes_adapter.assistant import Assistant, GatewayAssistant
from stash.hermes_adapter.callbacks import CallbackPress, FixCallbacks
from stash.hermes_adapter.events import DISPATCH_HOOK, Chat
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.wiring import build_callbacks, build_intake
from stash.llm import LlmError

POLL_SECONDS = 0.001
POLL_LIMIT_SECONDS = 2.0
CONFIRMATION_MESSAGE_ID = "900"

LoadConfig = Callable[[Path, Mapping[str, str]], StashConfig]


def unchanged(inner: CaptureIntake) -> CaptureIntake:
    return inner


def instant_bursts() -> BurstCoalescer:
    return BurstCoalescer(0.0)


def instant_config(path: Path, env: Mapping[str, str]) -> StashConfig:
    return a_stash_config(burst_window_seconds=0.0)


def app_over(
    rig: CaptureRig, wrap: Callable[[CaptureIntake], CaptureIntake] = unchanged, **overrides: Any
) -> StashApp:
    return an_app(
        **{
            "pipeline": wrap(SerializedPipeline(rig.pipeline)),
            "store": rig.store,
            "fixes": rig.fixes,
            **overrides,
        }
    )


async def until(predicate: Callable[[], object]) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + POLL_LIMIT_SECONDS
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError("condition was not met in time")
        await asyncio.sleep(POLL_SECONDS)


async def called(function: Callable[..., Any], *arguments: Any) -> Any:
    outcome = function(*arguments)
    return await outcome if inspect.isawaitable(outcome) else outcome


@dataclass(frozen=True, slots=True)
class HermesRig:
    capture: CaptureRig
    scheduler: PausingScheduler
    outbox: RecordingOutbox
    ctx: FakeHermesContext
    intake: MessageIntake
    callbacks: FixCallbacks

    async def deliver(self, *events: FakeEvent) -> list[dict[str, str]]:
        verdicts = [await self.ctx.dispatch(event) for event in events]
        await self.scheduler.drain()
        return verdicts

    async def confirmation_for(self, text: str = SAMPLE_TEXT) -> Reply:
        await self.deliver(an_event(text=text))
        return self.outbox.sent[0].reply

    def capture_statuses(self) -> list[CaptureStatus]:
        return [capture.status for capture in self.capture.store.stored_captures()]


def build_hermes_rig(
    answer: Mapping[str, object] | None = None,
    error: LlmError | None = None,
    links: Mapping[str, LinkInfo] | None = None,
    wrap: Callable[[CaptureIntake], CaptureIntake] = unchanged,
    owner_ids: str = OWNER_ID,
    outcomes: Sequence[Mapping[str, object] | LlmError] | None = None,
    assistant: Assistant | None = None,
) -> HermesRig:
    capture = build_rig(answer=answer, error=error, links=links, outcomes=outcomes)
    app = app_over(capture, wrap)
    scheduler = PausingScheduler()
    outbox = RecordingOutbox()
    owners = Owners.parse(owner_ids)
    ctx = a_hermes_context(owners=owners)
    intake = build_intake(app, owners, outbox, scheduler, sequential_ids())
    ctx.register_hook(DISPATCH_HOOK, intake.on_dispatch)
    return HermesRig(
        capture=capture,
        scheduler=scheduler,
        outbox=outbox,
        ctx=ctx,
        intake=intake,
        callbacks=build_callbacks(
            app, owners, outbox, assistant or GatewayAssistant(ctx.inject_message, outbox)
        ),
    )


def a_press(
    data: str,
    user_id: str = OWNER_ID,
    message_id: str = CONFIRMATION_MESSAGE_ID,
) -> CallbackPress:
    return CallbackPress(Chat(chat_id=OWNER_ID, user_id=user_id), message_id, data)


@dataclass(frozen=True, slots=True)
class ButtonRig:
    outbox: RecordingOutbox
    callbacks: FixCallbacks

    def pressed(self, data: str) -> str:
        asyncio.run(self.callbacks.on_press(a_press(data)))
        return self.outbox.edited[-1].reply.text


def build_button_rig(store: FreshStore) -> ButtonRig:
    outbox = RecordingOutbox()
    callbacks = build_callbacks(
        an_app(store=store), Owners.parse(OWNER_ID), outbox, RecordingAssistant()
    )
    return ButtonRig(outbox, callbacks)
