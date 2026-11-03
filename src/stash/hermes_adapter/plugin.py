import atexit
import logging
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from stash.app import StashApp, build_app
from stash.config import StashConfig
from stash.config.loader import expand_home, load_config
from stash.hermes_adapter.assistant import GatewayAssistant
from stash.hermes_adapter.host import hermes_secret, resolved_environment
from stash.hermes_adapter.outbox import LateBoundOutbox
from stash.hermes_adapter.owners import Owners
from stash.hermes_adapter.telegram_io import TelegramAttachment
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
DISPATCH_HOOK = "pre_gateway_dispatch"
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
            alias = f"stash_{name}"
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


def register(
    ctx: Any,
    *,
    env: Mapping[str, str] | None = None,
    read_secret: Callable[[str], str | None] = hermes_secret,
    build: Callable[[StashConfig], StashApp] = build_app,
    load: Callable[[Path, Mapping[str, str]], StashConfig] = load_config,
    at_exit: Callable[[Callable[[], None]], object] = atexit.register,
    new_id: Callable[[], str] = _new_message_id,
) -> None:
    environment = resolved_environment(
        os.environ if env is None else env, read_secret, HERMES_SECRETS
    )
    path = expand_home(str(ctx.get_config("config_path", DEFAULT_CONFIG_PATH)), environment)
    app = build(load(path, environment))
    at_exit(app.close)
    owners = Owners.parse(environment.get("TELEGRAM_ALLOWED_USERS"))
    if owners.admits_nobody():
        logger.warning("TELEGRAM_ALLOWED_USERS is empty: stash will ignore every message")
    outbox = LateBoundOutbox()
    assistant = GatewayAssistant(ctx.inject_message, outbox)
    intake = build_intake(app, owners, assistant, outbox, build_scheduler(app), new_id)
    callbacks = build_callbacks(app, owners, outbox, assistant)
    attachment = TelegramAttachment(outbox, callbacks.on_press)
    ctx.register_hook(DISPATCH_HOOK, intake.on_dispatch)
    ctx.register_platform_handler(
        "telegram", lambda application, adapter: attachment.attach(application)
    )
    _register_commands(ctx, build_commands(app))
    _register_tools(ctx, build_tools(app))
