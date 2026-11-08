import asyncio
import re
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from adapter_state_builders import an_adapter_state
from app_builders import an_app
from capture_builders import sequential_ids
from config_builders import a_stash_config
from fakes.hermes_ctx import FakeHermesContext
from fakes.pending_intake import PendingIntake
from fakes.recording_loader import RecordingLoader
from fakes.scripted_steps import ScriptedSteps
from hermes_ctx_builders import a_hermes_context
from hermes_events import OWNER_ID, an_event
from hermes_rig import called

from stash.app import StashApp
from stash.config import ConfigError, StashConfig
from stash.hermes_adapter.plugin import register

LOGGER = "stash.hermes_adapter.plugin"
HOME = "/home/owner"
OWNERS_ENV = {"TELEGRAM_ALLOWED_USERS": OWNER_ID, "HOME": HOME}


def no_secret(name: str) -> str | None:
    return None


def secrets(values: Mapping[str, str]) -> Callable[[str], str | None]:
    return values.get


def refusing_to_load(path: Path, environment: Mapping[str, str]) -> StashConfig:
    raise ConfigError("stash.toml is unreadable")


def register_plugin(
    ctx: FakeHermesContext | None = None,
    env: Mapping[str, str] | None = None,
    read_secret: Callable[[str], str | None] = no_secret,
    load: Callable[[Path, Mapping[str, str]], StashConfig] | None = None,
    app: StashApp | None = None,
    exits: list[Callable[[], None]] | None = None,
    new_id: Callable[[], str] | None = None,
) -> FakeHermesContext:
    context = ctx or a_hermes_context()
    built = app or an_app()
    register(
        context,
        new_id=new_id or sequential_ids(),
        env=OWNERS_ENV if env is None else env,
        read_secret=read_secret,
        build=lambda config: built,
        load=load or RecordingLoader(a_stash_config()),
        at_exit=(exits if exits is not None else []).append,
        state=an_adapter_state(),
    )
    return context


def test_a_tilde_path_without_a_home_in_the_environment_is_a_config_error() -> None:
    # Execute
    with pytest.raises(ConfigError) as refusal:
        register_plugin(env={})

    # Assert
    assert "HOME" in str(refusal.value)


def test_a_tilde_path_without_a_home_registers_nothing() -> None:
    # Setup
    ctx = a_hermes_context()

    # Execute
    with pytest.raises(ConfigError):
        register_plugin(ctx, env={})

    # Assert
    assert (ctx.hooks, ctx.commands, ctx.tools) == ({}, {}, {})


def test_the_owners_come_from_the_resolved_environment_not_the_raw_one() -> None:
    # Setup
    ctx = register_plugin(
        env={"TELEGRAM_ALLOWED_USERS": "7", "HOME": HOME},
        read_secret=secrets({"TELEGRAM_ALLOWED_USERS": "42"}),
    )

    # Execute
    verdict = asyncio.run(called(ctx.hooks["pre_gateway_dispatch"], an_event()))

    # Assert
    assert verdict == {"action": "skip"}


def message_ids_of_two_dispatched_events_without_one(
    new_id: Callable[[], str] | None,
) -> list[str]:
    steps = ScriptedSteps(PendingIntake())
    ctx = register_plugin(app=an_app(pipeline=steps), new_id=new_id)
    hook = ctx.hooks["pre_gateway_dispatch"]

    async def scenario() -> None:
        await called(hook, an_event(message_id=None))
        await called(hook, an_event(message_id=None))

    asyncio.run(scenario())
    return [message.source.message_id for message in steps.received]


def test_events_without_a_message_id_get_the_ids_of_the_injected_id_source() -> None:
    # Execute
    ids = message_ids_of_two_dispatched_events_without_one(sequential_ids())

    # Assert
    assert ids == [f"{1:032x}", f"{2:032x}"]


def message_ids_with_the_default_id_source() -> list[str]:
    steps = ScriptedSteps(PendingIntake())
    ctx = a_hermes_context()
    register(
        ctx,
        env=OWNERS_ENV,
        read_secret=no_secret,
        build=lambda config: an_app(pipeline=steps),
        load=RecordingLoader(a_stash_config()),
        at_exit=[].append,
        state=an_adapter_state(),
    )

    async def scenario() -> None:
        await called(ctx.hooks["pre_gateway_dispatch"], an_event(message_id=None))
        await called(ctx.hooks["pre_gateway_dispatch"], an_event(message_id=None))

    asyncio.run(scenario())
    return [message.source.message_id for message in steps.received]


def test_events_without_a_message_id_get_a_different_id_each_by_default() -> None:
    # Execute
    ids = message_ids_with_the_default_id_source()

    # Assert
    assert len(set(ids)) == 2


def test_default_message_ids_are_32_lowercase_hex_characters() -> None:
    # Execute
    ids = message_ids_with_the_default_id_source()

    # Assert
    assert all(re.fullmatch("[0-9a-f]{32}", message_id) for message_id in ids)
