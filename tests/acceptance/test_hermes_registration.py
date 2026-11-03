import asyncio
from collections.abc import Mapping
from pathlib import Path

import pytest
from capture_builders import a_filing_answer
from capture_rig import build_rig
from fakes.hermes_ctx import FakeHermesContext
from hermes_events import an_event
from hermes_rig import app_over, called, instant_bursts, register_stash, until
from telegram import InlineKeyboardMarkup

from stash.app import StashApp
from stash.capture import confirmation
from stash.config import ConfigError, StashConfig

QUESTION = "what can I do Saturday afternoon?"
COULD_NOT_HAND_OVER = "I couldn't pass that on to the assistant."


def a_plain_app() -> StashApp:
    return app_over(build_rig(), burst_factory=instant_bursts)


def refusing_to_load(path: Path, env: Mapping[str, str]) -> StashConfig:
    raise ConfigError("stash.toml is unreadable")


def test_register_adds_the_hook_the_telegram_handler_the_commands_and_the_tools() -> None:
    # Setup
    ctx = FakeHermesContext()

    # Execute
    register_stash(a_plain_app(), ctx)

    # Assert
    assert {
        "hooks": sorted(ctx.hooks),
        "platforms": sorted(ctx.platform_handlers),
        "commands": sorted(ctx.commands),
        "tools": {name: (tool.toolset, tool.schema["name"]) for name, tool in ctx.tools.items()},
    } == {
        "hooks": ["pre_gateway_dispatch"],
        "platforms": ["telegram"],
        "commands": ["gpu", "list", "retry"],
        "tools": {
            "stash_list": ("stash", "stash_list"),
            "stash_search": ("stash", "stash_search"),
        },
    }


def test_a_command_name_that_hermes_refuses_is_registered_with_a_stash_prefix_instead() -> None:
    # Setup
    ctx = FakeHermesContext(reserved={"retry"})

    # Execute
    register_stash(a_plain_app(), ctx)

    # Assert
    assert sorted(ctx.commands) == ["gpu", "list", "stash_retry"]


def test_an_invalid_configuration_makes_register_raise_the_config_error() -> None:
    # Setup
    app = a_plain_app()

    # Execute / Assert
    with pytest.raises(ConfigError):
        register_stash(app, load=refusing_to_load)


def test_the_owners_message_is_confirmed_through_telegram_with_the_item_buttons() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()

    async def scenario() -> dict[str, str]:
        verdict: dict[str, str] = await called(plugin.ctx.hooks["pre_gateway_dispatch"], an_event())
        await until(lambda: plugin.bot.sent)
        return verdict

    # Execute
    verdict = asyncio.run(scenario())

    # Assert
    [item] = rig.store.list_items()
    [sent] = plugin.bot.sent
    wire = [button.callback_data for row in sent.reply_markup.inline_keyboard for button in row]
    expected = [button.data for row in confirmation(item, unsure=False).buttons for button in row]
    assert (
        verdict,
        sent.chat_id,
        sent.text,
        isinstance(sent.reply_markup, InlineKeyboardMarkup),
        wire,
    ) == (
        {"action": "skip"},
        "42",
        "✅ Places · Tokyo · Want to",
        True,
        expected,
    )


def test_a_question_that_hermes_refuses_to_take_is_reported_to_the_owner_through_telegram() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer(route="request"))
    ctx = FakeHermesContext(inject_result=False)
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts), ctx)
    plugin.connect_telegram()

    async def scenario() -> None:
        await called(ctx.hooks["pre_gateway_dispatch"], an_event(text=QUESTION))
        await until(lambda: plugin.bot.sent)

    # Execute
    asyncio.run(scenario())

    # Assert
    assert ([message.content for message in ctx.injected], [m.text for m in plugin.bot.sent]) == (
        [QUESTION],
        [COULD_NOT_HAND_OVER],
    )
