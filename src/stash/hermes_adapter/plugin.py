import atexit
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from stash.app import StashApp, build_app
from stash.config import StashConfig
from stash.config.loader import expand_home, load_config
from stash.hermes_adapter.assistant import GatewayAssistant
from stash.hermes_adapter.events import DISPATCH_HOOK
from stash.hermes_adapter.host import hermes_secret, resolved_environment
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.telegram_link import TelegramLink
from stash.hermes_adapter.tools import LIST_SCHEMA, SEARCH_SCHEMA, TOOLSET, StashTools
from stash.hermes_adapter.wiring import (
    Command,
    build_callbacks,
    build_commands,
    build_intake,
    build_scheduler,
    build_tools,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "~/.config/stash/stash.toml"
HERMES_SECRETS = ("OPENROUTER_API_KEY", "TELEGRAM_ALLOWED_USERS")
COMMAND_DESCRIPTIONS = {
    "list": ("List saved items, newest first", "[stage]"),
    "gpu": ("Switch stash's use of the GPU", "on|off|status"),
    "retry": ("Retry captures that are still pending", ""),
}


def _new_message_id() -> str:
    return uuid4().hex


def _register_commands(ctx: Any, commands: Mapping[str, Command]) -> None:
    for name, command in commands.items():
        description, args_hint = COMMAND_DESCRIPTIONS[name]
        registered = ctx.register_command(
            name, command.run, description=description, args_hint=args_hint
        )
        if registered is None:
            alias = f"stash-{name}"
            logger.warning("Hermes refused /%s; registering it as /%s", name, alias)
            ctx.register_command(alias, command.run, description=description, args_hint=args_hint)


def _register_tools(ctx: Any, tools: StashTools) -> None:
    for schema, handler in ((SEARCH_SCHEMA, tools.search), (LIST_SCHEMA, tools.list_items)):
        ctx.register_tool(
            name=schema["name"],
            toolset=TOOLSET,
            schema=schema,
            handler=handler,
            description=schema["description"],
        )


class SharedApp:
    def __init__(self) -> None:
        self._app: StashApp | None = None

    def open_once(
        self, opener: Callable[[], StashApp], at_exit: Callable[[Callable[[], None]], object]
    ) -> StashApp:
        if self._app is None:
            app = opener()
            at_exit(app.close)
            self._app = app
        else:
            logger.info("reusing the open stash app; restart the gateway to reload stash.toml")
        return self._app


@dataclass(frozen=True, slots=True)
class AdapterState:
    app: SharedApp
    telegram: TelegramLink


# Unverified (spike-m0 #24): outlives a hot-reload; Hermes re-imports only the shim, not stash.*
PROCESS_STATE = AdapterState(SharedApp(), TelegramLink())


def _wire_chat(
    ctx: Any, app: StashApp, owners: Owners, link: TelegramLink, new_id: Callable[[], str]
) -> None:
    assistant = GatewayAssistant(ctx.inject_message, link.outbox)
    intake = build_intake(app, owners, link.outbox, build_scheduler(app), new_id)
    callbacks = build_callbacks(app, owners, link.outbox, assistant)
    link.route_presses_to(callbacks.on_press)
    ctx.register_hook(DISPATCH_HOOK, intake.on_dispatch)
    ctx.register_platform_handler("telegram", link.on_connect)


def register(
    ctx: Any,
    *,
    env: Mapping[str, str] | None = None,
    read_secret: Callable[[str], str | None] = hermes_secret,
    build: Callable[[StashConfig], StashApp] = build_app,
    load: Callable[[Path, Mapping[str, str]], StashConfig] = load_config,
    at_exit: Callable[[Callable[[], None]], object] = atexit.register,
    new_id: Callable[[], str] = _new_message_id,
    state: AdapterState = PROCESS_STATE,
) -> None:
    environment = resolved_environment(
        os.environ if env is None else env, read_secret, HERMES_SECRETS
    )
    path = expand_home(str(ctx.get_config("config_path", DEFAULT_CONFIG_PATH)), environment)
    app = state.app.open_once(lambda: build(load(path, environment)), at_exit)
    owners = Owners.parse(environment.get("TELEGRAM_ALLOWED_USERS"))
    if owners.admits_nobody():
        logger.warning("TELEGRAM_ALLOWED_USERS is empty: stash will ignore every message")
    _wire_chat(ctx, app, owners, state.telegram, new_id)
    _register_commands(ctx, build_commands(app))
    _register_tools(ctx, build_tools(app))
