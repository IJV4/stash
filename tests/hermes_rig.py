import asyncio
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_builders import an_app
from capture_builders import sequential_ids
from capture_rig import CaptureRig, build_rig
from config_builders import a_stash_config
from fakes.fake_telegram_bot import FakeTelegramApplication, FakeTelegramBot
from fakes.hermes_ctx import FakeHermesContext
from fakes.pausing_scheduler import PausingScheduler
from fakes.recording_assistant import RecordingAssistant
from fakes.recording_outbox import RecordingOutbox
from hermes_events import OWNER_ID, an_event

from stash.app import StashApp
from stash.capture import BurstCoalescer, CaptureIntake, Reply, SerializedPipeline
from stash.config import StashConfig
from stash.enrich.links import LinkInfo
from stash.hermes_adapter.callbacks import CallbackPress, FixCallbacks
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.intake import MessageIntake
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.plugin import register
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
    app: StashApp
    scheduler: PausingScheduler
    outbox: RecordingOutbox
    assistant: RecordingAssistant
    intake: MessageIntake
    callbacks: FixCallbacks

    async def confirmation_for(self, text: str = "Ramen in Shibuya") -> Reply:
        await self.intake.on_dispatch(an_event(text=text))
        await self.scheduler.drain()
        return self.outbox.sent[0].reply


def build_hermes_rig(
    answer: Mapping[str, object] | None = None,
    error: LlmError | None = None,
    links: Mapping[str, LinkInfo] | None = None,
    wrap: Callable[[CaptureIntake], CaptureIntake] = unchanged,
    owner_ids: str = OWNER_ID,
) -> HermesRig:
    capture = build_rig(answer=answer, error=error, links=links)
    app = app_over(capture, wrap)
    scheduler = PausingScheduler()
    outbox = RecordingOutbox()
    assistant = RecordingAssistant()
    owners = Owners.parse(owner_ids)
    return HermesRig(
        capture=capture,
        app=app,
        scheduler=scheduler,
        outbox=outbox,
        assistant=assistant,
        intake=build_intake(app, owners, assistant, outbox, scheduler, sequential_ids()),
        callbacks=build_callbacks(app, owners, outbox, assistant),
    )


def a_press(
    data: str,
    user_id: str = OWNER_ID,
    message_id: str = CONFIRMATION_MESSAGE_ID,
) -> CallbackPress:
    return CallbackPress(Chat(chat_id=OWNER_ID, user_id=user_id), message_id, data)


@dataclass(frozen=True, slots=True)
class RegisteredStash:
    ctx: FakeHermesContext
    application: FakeTelegramApplication
    exits: list[Callable[[], None]]

    @property
    def bot(self) -> FakeTelegramBot:
        return self.application.bot

    def connect_telegram(self) -> None:
        self.ctx.platform_handlers["telegram"](self.application, None)


def register_stash(
    app: StashApp,
    ctx: FakeHermesContext | None = None,
    load: LoadConfig = instant_config,
    owner_ids: str = OWNER_ID,
) -> RegisteredStash:
    context = FakeHermesContext() if ctx is None else ctx
    exits: list[Callable[[], None]] = []
    register(
        context,
        env={"TELEGRAM_ALLOWED_USERS": owner_ids, "HOME": "/home/owner"},
        read_secret=lambda name: None,
        build=lambda config: app,
        load=load,
        at_exit=exits.append,
    )
    return RegisteredStash(context, FakeTelegramApplication(), exits)
