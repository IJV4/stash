import asyncio
import logging
from typing import Any

import pytest
from fakes.fake_telegram_bot import FakeTelegramApplication
from fakes.ptb_callback_updates import AnsweringBot, callback_update
from fakes.recording_presses import PressLog
from log_records import recording_logs

from stash.capture import Reply
from stash.hermes_adapter.callbacks import CallbackPress
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.outbox import OutboxUnavailable
from stash.hermes_adapter.telegram_link import START_UP_FAILED_LOG, TelegramLink

TELEGRAM_IO_LOGGER = "stash.hermes_adapter.telegram_io"
TELEGRAM_LINK_LOGGER = "stash.hermes_adapter.telegram_link"
PLAIN = Reply("Saved")
OUTBOX_NOT_UP = "the Telegram connection is not up yet"


def press_through(application: FakeTelegramApplication, **update_fields: Any) -> None:
    handler: Any = application.handlers[0]
    asyncio.run(handler.callback(callback_update(AnsweringBot([]), **update_fields), None))


def test_the_outbox_is_unavailable_until_telegram_connects() -> None:
    # Setup
    link = TelegramLink()

    # Execute
    with pytest.raises(OutboxUnavailable) as refusal:
        asyncio.run(link.outbox.send("1001", PLAIN))

    # Assert
    assert str(refusal.value) == OUTBOX_NOT_UP


def test_the_outbox_handed_out_before_connecting_sends_through_the_connected_bot() -> None:
    # Setup
    link = TelegramLink()
    outbox = link.outbox
    application = FakeTelegramApplication()

    # Execute
    link.on_connect(application, None)
    asyncio.run(outbox.send("1001", PLAIN))

    # Assert
    assert [(sent.chat_id, sent.text) for sent in application.bot.sent] == [("1001", "Saved")]


def test_a_press_is_answered_by_the_handler_the_link_is_routed_to() -> None:
    # Setup
    link = TelegramLink()
    presses = PressLog()
    link.route_presses_to(presses)
    application = FakeTelegramApplication()
    link.on_connect(application, None)

    # Execute
    press_through(application, data="stash:t:abc", chat_id=1001, user_id=42, message_id=55)

    # Assert
    assert presses.presses == [CallbackPress(Chat("1001", "42"), "55", "stash:t:abc")]


def test_a_press_after_routing_again_is_answered_by_the_newest_handler_only() -> None:
    # Setup
    link = TelegramLink()
    older, newer = PressLog(), PressLog()
    link.route_presses_to(older)
    application = FakeTelegramApplication()
    link.on_connect(application, None)
    link.route_presses_to(newer)

    # Execute
    press_through(application)

    # Assert
    assert (len(older.presses), len(newer.presses)) == (0, 1)


def test_a_press_before_any_handler_is_routed_is_logged_as_a_failure_and_not_raised() -> None:
    # Setup
    link = TelegramLink()
    application = FakeTelegramApplication()
    link.on_connect(application, None)

    # Execute
    with recording_logs(TELEGRAM_IO_LOGGER) as logs:
        press_through(application, chat_id=1001)

    # Assert
    assert logs.entries() == [(logging.ERROR, "callback press failed for chat 1001")]


def test_a_start_up_callback_that_fails_is_logged_and_not_raised() -> None:
    # Setup
    link = TelegramLink()

    def failing() -> None:
        raise RuntimeError("no running loop")

    link.start_with(failing)

    # Execute
    with recording_logs(TELEGRAM_LINK_LOGGER) as logs:
        link.on_connect(FakeTelegramApplication(), None)

    # Assert
    assert logs.entries() == [(logging.ERROR, START_UP_FAILED_LOG)]
