import asyncio
import logging
import re
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from adapter_state_builders import an_adapter_state
from app_builders import an_app
from capture_builders import sequential_ids
from config_builders import a_stash_config
from fakes.close_counter import CloseCounter
from fakes.fake_suggestion_desk import FakeSuggestionDesk
from fakes.hermes_ctx import FakeHermesContext
from fakes.pending_intake import PendingIntake
from fakes.recording_loader import RecordingLoader
from fakes.scripted_steps import ScriptedSteps
from hermes_ctx_builders import a_hermes_context
from hermes_events import OWNER_ID, an_event
from hermes_rig import called
from log_records import recording_logs
from suggestion_picks import a_pick

from stash.app import StashApp
from stash.config import ConfigError, StashConfig
from stash.hermes_adapter.capture_tools import CAPTURE_SCHEMA
from stash.hermes_adapter.lifecycle_schemas import (
    ANNOTATE_SCHEMA,
    COMPLETE_SCHEMA,
    GET_SCHEMA,
    GROUP_SCHEMA,
    KEEP_SCHEMA,
    LIBRARY_SCHEMA,
    SET_STAGE_SCHEMA,
)
from stash.hermes_adapter.plugin import register
from stash.hermes_adapter.step_schemas import (
    ADD_STEP_SCHEMA,
    COMPLETE_STEP_SCHEMA,
    EDIT_STEP_SCHEMA,
)
from stash.hermes_adapter.suggest_tools import SUGGEST_SCHEMA
from stash.hermes_adapter.tools import LIST_SCHEMA, SEARCH_SCHEMA
from stash.suggestions import Picked

LIFECYCLE_SCHEMAS = (
    GET_SCHEMA,
    COMPLETE_SCHEMA,
    ANNOTATE_SCHEMA,
    SET_STAGE_SCHEMA,
    KEEP_SCHEMA,
    GROUP_SCHEMA,
    LIBRARY_SCHEMA,
)
STEP_SCHEMAS = (ADD_STEP_SCHEMA, EDIT_STEP_SCHEMA, COMPLETE_STEP_SCHEMA)
LOGGER = "stash.hermes_adapter.plugin"
HOME = "/home/owner"
DEFAULT_PATH = Path("/home/owner/.config/stash/stash.toml")
OWNERS_ENV = {"TELEGRAM_ALLOWED_USERS": OWNER_ID, "HOME": HOME}
ABSOLUTE_CONFIG = {"config_path": "/etc/stash/stash.toml"}


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


def loaded_path(ctx: FakeHermesContext, env: Mapping[str, str]) -> Path:
    loader = RecordingLoader(a_stash_config())
    register_plugin(ctx, env=env, load=loader)
    return loader.calls[0].path


def loaded_environment(
    env: Mapping[str, str], read_secret: Callable[[str], str | None]
) -> Mapping[str, str]:
    loader = RecordingLoader(a_stash_config())
    register_plugin(
        a_hermes_context(config=ABSOLUTE_CONFIG),
        env=env,
        read_secret=read_secret,
        load=loader,
    )
    return loader.calls[0].environment


def test_the_default_config_path_is_under_the_home_of_the_resolved_environment() -> None:
    # Execute
    path = loaded_path(a_hermes_context(), {"HOME": HOME})

    # Assert
    assert path == DEFAULT_PATH


def test_a_configured_path_is_used_instead_of_the_default() -> None:
    # Setup
    ctx = a_hermes_context(config={"config_path": "/etc/stash/stash.toml"})

    # Execute
    path = loaded_path(ctx, {"HOME": HOME})

    # Assert
    assert path == Path("/etc/stash/stash.toml")


def test_a_configured_path_under_the_tilde_is_expanded_with_the_resolved_home() -> None:
    # Setup
    ctx = a_hermes_context(config={"config_path": "~/notes/stash.toml"})

    # Execute
    path = loaded_path(ctx, {"HOME": HOME})

    # Assert
    assert path == Path("/home/owner/notes/stash.toml")


def test_a_bare_tilde_is_the_resolved_home() -> None:
    # Setup
    ctx = a_hermes_context(config={"config_path": "~"})

    # Execute
    path = loaded_path(ctx, {"HOME": HOME})

    # Assert
    assert path == Path(HOME)


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


def test_a_path_that_only_starts_with_a_tilde_is_not_expanded() -> None:
    # Setup
    ctx = a_hermes_context(config={"config_path": "~owner/stash.toml"})

    # Execute
    path = loaded_path(ctx, {"HOME": HOME})

    # Assert
    assert path == Path("~owner/stash.toml")


def test_a_hermes_secret_wins_over_the_environment_value() -> None:
    # Execute
    environment = loaded_environment(
        {"OPENROUTER_API_KEY": "sk-from-env"}, secrets({"OPENROUTER_API_KEY": "sk-from-hermes"})
    )

    # Assert
    assert environment == {
        "OPENROUTER_API_KEY": "sk-from-hermes",
    }


def test_a_missing_hermes_secret_leaves_the_environment_value() -> None:
    # Execute
    environment = loaded_environment({"OPENROUTER_API_KEY": "sk-from-env"}, no_secret)

    # Assert
    assert environment == {"OPENROUTER_API_KEY": "sk-from-env"}


def test_the_telegram_allowed_users_secret_is_part_of_the_resolved_environment() -> None:
    # Execute
    environment = loaded_environment({}, secrets({"TELEGRAM_ALLOWED_USERS": "42,43"}))

    # Assert
    assert environment == {"TELEGRAM_ALLOWED_USERS": "42,43"}


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


def test_the_application_is_closed_through_exactly_one_exit_hook() -> None:
    # Setup
    resources = CloseCounter()
    exits: list[Callable[[], None]] = []
    register_plugin(app=an_app(resources=resources), exits=exits)

    # Execute
    for close in exits:
        close()

    # Assert
    assert resources.closes == 1


def test_nothing_is_closed_while_registering() -> None:
    # Setup
    resources = CloseCounter()

    # Execute
    register_plugin(app=an_app(resources=resources))

    # Assert
    assert resources.closes == 0


def test_a_config_error_leaves_nothing_registered_and_no_exit_hook() -> None:
    # Setup
    ctx = a_hermes_context()
    exits: list[Callable[[], None]] = []

    # Execute
    with pytest.raises(ConfigError):
        register_plugin(ctx, load=refusing_to_load, exits=exits)

    # Assert
    assert (ctx.hooks, ctx.platform_handlers, ctx.commands, ctx.tools, exits) == (
        {},
        {},
        {},
        {},
        [],
    )


def warning_levels(env: Mapping[str, str]) -> list[int]:
    with recording_logs(LOGGER) as logs:
        register_plugin(env={"HOME": HOME, **env})
    return [level for level, _ in logs.entries()]


def test_missing_owners_log_one_warning() -> None:
    # Execute
    levels = warning_levels({})

    # Assert
    assert levels == [logging.WARNING]


def test_blank_owners_log_one_warning() -> None:
    # Execute
    levels = warning_levels({"TELEGRAM_ALLOWED_USERS": " , "})

    # Assert
    assert levels == [logging.WARNING]


def test_configured_owners_log_no_warning() -> None:
    # Execute
    levels = warning_levels(OWNERS_ENV)

    # Assert
    assert levels == []


def test_the_hook_is_registered_even_when_there_are_no_owners() -> None:
    # Execute
    ctx = register_plugin(env={"HOME": HOME})

    # Assert
    assert sorted(ctx.hooks) == ["pre_gateway_dispatch"]


def test_commands_are_registered_with_their_argument_hints() -> None:
    # Execute
    ctx = register_plugin()

    # Assert
    assert {c.name: c.args_hint for c in ctx.command_registrations} == {
        "list": "[stage]",
        "gpu": "on|off|status",
        "retry": "",
        "library": "[type]",
        "suggest": "[context]",
    }


def test_commands_are_registered_with_their_descriptions() -> None:
    # Execute
    ctx = register_plugin()

    # Assert
    assert {c.name: c.description for c in ctx.command_registrations} == {
        "list": "List saved items, newest first",
        "gpu": "Switch stash's use of the GPU",
        "retry": "Retry captures that are still pending",
        "library": "List kept items, most recently finished first",
        "suggest": "Suggest what to do from Want to",
    }


def test_a_refused_command_keeps_its_argument_hint_and_description_under_the_prefixed_name() -> (
    None
):
    # Setup
    ctx = a_hermes_context(reserved={"gpu"})

    # Execute
    register_plugin(ctx)

    # Assert
    [gpu] = [c for c in ctx.command_registrations if c.name == "stash-gpu"]
    assert (gpu.args_hint, gpu.description) == ("on|off|status", "Switch stash's use of the GPU")


def test_a_refused_suggest_command_keeps_its_hint_and_description_under_the_prefixed_name() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"suggest"})

    # Execute
    register_plugin(ctx)

    # Assert
    [suggest] = [c for c in ctx.command_registrations if c.name == "stash-suggest"]
    assert (suggest.args_hint, suggest.description) == (
        "[context]",
        "Suggest what to do from Want to",
    )


def test_a_refused_suggest_command_still_answers_from_the_apps_suggestions() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked((a_pick("d1", "Dune", "A quiet read"),)))
    ctx = a_hermes_context(reserved={"suggest"})
    register_plugin(ctx, app=an_app(suggestions=desk))

    # Execute
    answer = asyncio.run(called(ctx.commands["stash-suggest"], "at home"))

    # Assert
    assert (answer, desk.asked) == ("• Dune — A quiet read", [("at home", 3)])


def test_a_registered_suggest_command_is_not_registered_under_a_prefix() -> None:
    # Execute
    ctx = register_plugin()

    # Assert
    assert "stash-suggest" not in ctx.commands


def test_a_refused_command_runs_the_same_command_under_the_prefixed_name() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"retry"})
    register_plugin(ctx)

    # Execute
    answer = asyncio.run(called(ctx.commands["stash-retry"], ""))

    # Assert
    assert answer == "Nothing pending."


def test_a_refused_command_is_found_by_the_gateways_underscore_to_hyphen_lookup() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"retry"})
    register_plugin(ctx)
    typed_in_telegram = "stash_retry"

    # Execute
    found = ctx.commands.get(typed_in_telegram.replace("_", "-"))

    # Assert
    assert found is not None


def test_a_refused_command_is_logged_as_one_warning() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"list"})

    # Execute
    with recording_logs(LOGGER) as logs:
        register_plugin(ctx)

    # Assert
    assert [level for level, _ in logs.entries()] == [logging.WARNING]


def test_a_refused_command_is_not_registered_under_its_own_name() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"list"})

    # Execute
    register_plugin(ctx)

    # Assert
    assert "list" not in ctx.commands


def test_tools_are_registered_with_the_description_of_their_schema() -> None:
    # Execute
    ctx = register_plugin()

    # Assert
    assert {name: tool.description for name, tool in ctx.tools.items()} == {
        "stash_search": SEARCH_SCHEMA["description"],
        "stash_list": LIST_SCHEMA["description"],
        **{schema["name"]: schema["description"] for schema in LIFECYCLE_SCHEMAS},
        "stash_capture": CAPTURE_SCHEMA["description"],
        **{schema["name"]: schema["description"] for schema in STEP_SCHEMAS},
        "stash_suggest": SUGGEST_SCHEMA["description"],
    }


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
