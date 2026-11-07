import asyncio
import logging
from typing import Any

import pytest
from app_builders import an_app
from fakes.scripted_deliveries import ScriptedNudges
from hermes_ctx_builders import a_hermes_context
from hermes_registration_rig import RegisteredStash, register_stash
from hermes_rig import until
from log_records import recording_logs

from stash.capture import Reply
from stash.hermes_adapter.plugin import NO_OWNER_CHAT_LOG

PLUGIN_LOGGER = "stash.hermes_adapter.plugin"
OWNERS = "77,42"
NEW_OWNER = "99"
OWNER_CHAT_SETTING = "owner_chat_id"


def a_stash_with_a_reminder_due(owner_ids: str, **config: Any) -> RegisteredStash:
    app = an_app(nudge_delivery=ScriptedNudges(replies=(Reply("Book the table"),)))
    return register_stash(app, a_hermes_context(config=config), owner_ids=owner_ids)


async def chat_messaged_after_connecting(plugin: RegisteredStash) -> str:
    plugin.ctx.connect("telegram", plugin.application)
    await until(lambda: plugin.bot.sent)
    await plugin.ctx.cancel_spawned()
    return plugin.bot.sent[0].chat_id


@pytest.mark.parametrize(
    ("config", "expected_chat"),
    [
        pytest.param({}, "77", id="first-allowed-user"),
        pytest.param({OWNER_CHAT_SETTING: "-100123"}, "-100123", id="setting-overrides"),
        pytest.param({OWNER_CHAT_SETTING: "  "}, "77", id="blank-setting-ignored"),
        pytest.param({OWNER_CHAT_SETTING: 555}, "555", id="numeric-setting"),
    ],
)
def test_reminders_go_to_the_owner_chat_chosen_from_the_settings_and_allowed_users(
    config: dict[str, Any], expected_chat: str
) -> None:
    # Setup
    plugin = a_stash_with_a_reminder_due(OWNERS, **config)

    # Execute
    chat = asyncio.run(chat_messaged_after_connecting(plugin))

    # Assert
    assert chat == expected_chat


def test_with_no_owner_chat_no_ticker_starts_and_one_warning_says_reminders_are_off() -> None:
    # Setup
    with recording_logs(PLUGIN_LOGGER) as logs:
        plugin = a_stash_with_a_reminder_due("")

    # Execute
    plugin.connect_telegram()

    # Assert
    assert (plugin.ctx.spawned, logs.entries().count((logging.WARNING, NO_OWNER_CHAT_LOG))) == (
        [],
        1,
    )


def test_a_second_register_points_the_reminders_at_the_newest_owner_chat() -> None:
    # Setup
    reloaded = a_stash_with_a_reminder_due(OWNERS).reloaded(owner_ids=NEW_OWNER)

    # Execute
    chat = asyncio.run(chat_messaged_after_connecting(reloaded))

    # Assert
    assert chat == NEW_OWNER
