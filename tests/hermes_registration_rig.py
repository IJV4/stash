import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from adapter_state_builders import an_adapter_state
from capture_rig import CaptureRig
from fakes.close_counter import CloseCounter
from fakes.fake_telegram_bot import FakeTelegramApplication, FakeTelegramBot
from fakes.hermes_ctx import FakeHermesContext
from fakes.ptb_callback_updates import AnsweringBot, callback_update
from hermes_ctx_builders import a_hermes_context
from hermes_events import OWNER_ID, FakeEvent
from hermes_rig import CONFIRMATION_MESSAGE_ID, LoadConfig, app_over, instant_config

from stash.app import StashApp
from stash.config import StashConfig
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.plugin import register

BuildApp = Callable[[StashConfig], StashApp]


class OpenedApps:
    def __init__(self, capture: CaptureRig, **overrides: Any) -> None:
        self._capture = capture
        self._overrides = overrides
        self._counters: list[CloseCounter] = []

    def __call__(self, config: StashConfig) -> StashApp:
        counter = CloseCounter()
        self._counters.append(counter)
        return app_over(self._capture, resources=counter, **self._overrides)

    @property
    def built(self) -> int:
        return len(self._counters)

    def still_open(self) -> int:
        return sum(1 for counter in self._counters if counter.closes == 0)


@dataclass(frozen=True, slots=True)
class RegisteredStash:
    ctx: FakeHermesContext
    application: FakeTelegramApplication
    exits: list[Callable[[], None]]
    owner_ids: str
    register_into: Callable[[FakeHermesContext, str], None]

    @property
    def bot(self) -> FakeTelegramBot:
        return self.application.bot

    def connect_telegram(self) -> None:
        asyncio.run(self._connect_without_ticking())

    async def _connect_without_ticking(self) -> None:
        self.ctx.connect("telegram", self.application)
        await self.ctx.cancel_spawned()

    def reconnected(self) -> "RegisteredStash":
        reconnected = replace(self, application=FakeTelegramApplication())
        reconnected.connect_telegram()
        return reconnected

    def register_again(self) -> None:
        self.register_into(self.ctx, self.owner_ids)

    def reloaded(self, owner_ids: str | None = None) -> "RegisteredStash":
        ids = self.owner_ids if owner_ids is None else owner_ids
        successor = self.ctx.reloaded(owners=Owners.parse(ids))
        self.register_into(successor, ids)
        return replace(self, ctx=successor, owner_ids=ids)

    async def dispatch(self, event: FakeEvent) -> dict[str, str]:
        return await self.ctx.dispatch(event)

    def sent_button_data(self, label: str) -> str:
        [sent, *_] = self.bot.sent
        return next(
            button.callback_data
            for row in sent.reply_markup.inline_keyboard
            for button in row
            if button.text == label
        )

    async def press(self, data: str, message_id: int = int(CONFIRMATION_MESSAGE_ID)) -> None:
        update = callback_update(
            AnsweringBot([]),
            data=data,
            chat_id=int(OWNER_ID),
            user_id=int(OWNER_ID),
            message_id=message_id,
        )
        await self.application.handlers[0].callback(update, None)


def register_stash_over(
    build: BuildApp,
    ctx: FakeHermesContext | None = None,
    load: LoadConfig = instant_config,
    owner_ids: str = OWNER_ID,
) -> RegisteredStash:
    context = a_hermes_context(owners=Owners.parse(owner_ids)) if ctx is None else ctx
    exits: list[Callable[[], None]] = []
    state = an_adapter_state()

    def register_into(target: FakeHermesContext, allowed_users: str) -> None:
        register(
            target,
            env={"TELEGRAM_ALLOWED_USERS": allowed_users, "HOME": "/home/owner"},
            read_secret=lambda name: None,
            build=build,
            load=load,
            at_exit=exits.append,
            state=state,
        )

    register_into(context, owner_ids)
    return RegisteredStash(context, FakeTelegramApplication(), exits, owner_ids, register_into)


def register_stash(
    app: StashApp,
    ctx: FakeHermesContext | None = None,
    load: LoadConfig = instant_config,
    owner_ids: str = OWNER_ID,
) -> RegisteredStash:
    return register_stash_over(lambda config: app, ctx, load, owner_ids)
