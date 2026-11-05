import asyncio
from collections.abc import Mapping
from pathlib import Path

import pytest
from capture_builders import QUESTION, a_filing_answer, a_request_answer, an_unsure_answer
from capture_rig import build_rig
from hermes_ctx_builders import a_hermes_context
from hermes_events import ALLOW, OWNER_ID, SKIP, an_event
from hermes_registration_rig import OpenedApps, register_stash, register_stash_over
from hermes_rig import CONFIRMATION_MESSAGE_ID, app_over, called, instant_bursts, until
from telegram import InlineKeyboardMarkup

from stash.app import StashApp
from stash.capture import confirmation
from stash.config import ConfigError, StashConfig
from stash.hermes_adapter.assistant import APOLOGY

QUESTION_BUTTON = "That was a question →"


def a_plain_app() -> StashApp:
    return app_over(build_rig(), burst_factory=instant_bursts)


def refusing_to_load(path: Path, env: Mapping[str, str]) -> StashConfig:
    raise ConfigError("stash.toml is unreadable")


def test_register_adds_the_hook_the_telegram_handler_the_commands_and_the_tools() -> None:
    # Setup
    ctx = a_hermes_context()

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
        "commands": ["gpu", "library", "list", "retry"],
        "tools": {
            "stash_annotate": ("stash", "stash_annotate"),
            "stash_complete": ("stash", "stash_complete"),
            "stash_get": ("stash", "stash_get"),
            "stash_group": ("stash", "stash_group"),
            "stash_keep": ("stash", "stash_keep"),
            "stash_library": ("stash", "stash_library"),
            "stash_list": ("stash", "stash_list"),
            "stash_search": ("stash", "stash_search"),
            "stash_set_stage": ("stash", "stash_set_stage"),
        },
    }


def test_a_command_name_that_hermes_refuses_is_registered_with_a_stash_prefix_instead() -> None:
    # Setup
    ctx = a_hermes_context(reserved={"retry"})

    # Execute
    register_stash(a_plain_app(), ctx)

    # Assert
    assert sorted(ctx.commands) == ["gpu", "library", "list", "stash-retry"]


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
        SKIP,
        "42",
        "✅ Places · Tokyo · Want to",
        True,
        expected,
    )


def test_a_question_dispatched_through_hermes_is_allowed_and_nothing_is_injected() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())
    ctx = a_hermes_context()
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts), ctx)

    # Execute
    verdict = asyncio.run(plugin.dispatch(an_event(text=QUESTION)))

    # Assert
    assert (verdict, ctx.injected, ctx.refused) == (ALLOW, [], [])


def test_that_was_a_question_pressed_through_telegram_apologises_with_no_allowed_question() -> None:
    # Setup
    rig = build_rig(outcomes=[an_unsure_answer()])
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()

    async def scenario() -> None:
        await plugin.dispatch(an_event(text=QUESTION))
        await until(lambda: plugin.bot.sent)
        await plugin.press(plugin.sent_button_data(QUESTION_BUTTON))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (
        [message.content for message in plugin.ctx.refused],
        plugin.ctx.injected,
        [sent.text for sent in plugin.bot.sent[1:]],
    ) == ([QUESTION], [], [APOLOGY.text])


def test_that_was_a_question_pressed_through_telegram_injects_the_text_after_a_question() -> None:
    # Setup
    rig = build_rig(outcomes=[a_request_answer(), an_unsure_answer()])
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()

    async def scenario() -> None:
        await plugin.dispatch(an_event(text="what is on my list?", message_id="q1"))
        await plugin.dispatch(an_event(text=QUESTION, message_id="q2"))
        await until(lambda: plugin.bot.sent)
        await plugin.press(plugin.sent_button_data(QUESTION_BUTTON))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert (
        [message.content for message in plugin.ctx.injected],
        plugin.ctx.refused,
        len(plugin.bot.sent),
    ) == ([QUESTION], [], 1)


def test_after_a_second_register_the_owners_message_is_still_confirmed_through_telegram() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()
    plugin.register_again()

    async def scenario() -> None:
        await plugin.dispatch(an_event())
        await until(lambda: plugin.bot.sent)

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [sent.text for sent in plugin.bot.sent] == ["✅ Places · Tokyo · Want to"]


def test_after_a_second_register_a_question_is_allowed_and_reaches_the_agent_once() -> None:
    # Setup
    rig = build_rig(answer=a_request_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()
    reloaded = plugin.reloaded()

    # Execute
    verdict = asyncio.run(reloaded.dispatch(an_event(text=QUESTION)))

    # Assert
    assert (verdict, reloaded.ctx.injected, reloaded.ctx.refused) == (ALLOW, [], [])


def test_after_a_second_register_a_button_press_edits_its_confirmation() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()
    plugin.register_again()

    async def scenario() -> None:
        await plugin.dispatch(an_event())
        await until(lambda: plugin.bot.sent)
        await plugin.press(plugin.sent_button_data("Type"))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [(edited.chat_id, edited.message_id) for edited in plugin.bot.edited] == [
        (OWNER_ID, int(CONFIRMATION_MESSAGE_ID))
    ]


def test_after_a_second_register_the_commands_answer_in_the_reloaded_context() -> None:
    # Setup
    plugin = register_stash(a_plain_app())
    plugin.connect_telegram()
    reloaded = plugin.reloaded()

    # Execute
    answer = asyncio.run(called(reloaded.ctx.commands["retry"], ""))

    # Assert
    assert answer == "Nothing pending."


def test_after_a_second_register_a_new_telegram_application_confirms_and_edits_through_it() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    plugin.connect_telegram()
    reconnected = plugin.reloaded().reconnected()

    async def scenario() -> None:
        await reconnected.dispatch(an_event())
        await until(lambda: reconnected.bot.sent)
        await reconnected.press(reconnected.sent_button_data("Type"))

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [(edited.chat_id, edited.message_id) for edited in reconnected.bot.edited] == [
        (OWNER_ID, int(CONFIRMATION_MESSAGE_ID))
    ]


def test_a_second_register_before_telegram_first_connects_still_confirms_the_owners_message() -> (
    None
):
    # Setup
    rig = build_rig(answer=a_filing_answer())
    plugin = register_stash(app_over(rig, burst_factory=instant_bursts))
    reloaded = plugin.reloaded()
    reloaded.connect_telegram()

    async def scenario() -> None:
        await reloaded.dispatch(an_event())
        await until(lambda: reloaded.bot.sent)

    # Execute
    asyncio.run(scenario())

    # Assert
    assert [sent.text for sent in reloaded.bot.sent] == ["✅ Places · Tokyo · Want to"]


def test_after_a_second_register_one_app_stays_open() -> None:
    # Setup
    apps = OpenedApps(build_rig(), burst_factory=instant_bursts)
    plugin = register_stash_over(apps)
    plugin.register_again()
    open_before_exit = apps.still_open()

    # Execute
    for close in plugin.exits:
        close()

    # Assert
    assert (open_before_exit, len(plugin.exits), apps.still_open()) == (1, 1, 0)
