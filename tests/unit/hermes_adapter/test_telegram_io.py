import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from builders import an_item_at
from fakes.fake_telegram_bot import FakeTelegramApplication, FakeTelegramBot
from fakes.keyword_only_telegram_bot import KeywordOnlyTelegramBot
from fakes.ptb_callback_updates import AnsweringBot, callback_update
from fakes.recording_presses import PressLog
from log_records import recording_logs
from telegram import Bot, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import CallbackQueryHandler

from stash.capture import Button, Reply, stage_menu
from stash.domain import Stage
from stash.hermes_adapter.callbacks import CallbackPress
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.outbox import LateBoundOutbox, OutboxUnavailable
from stash.hermes_adapter.telegram_io import TelegramAttachment, TelegramOutbox, to_keyboard

TELEGRAM_IO_LOGGER = "stash.hermes_adapter.telegram_io"
PLAIN = Reply("Saved")
WITH_BUTTONS = Reply(
    "Saved as a note",
    (
        (Button("Type", "stash:t:abc"), Button("Stage", "stash:s:abc")),
        (Button("Undo", "stash:u:abc"),),
    ),
)
TWO_DONE_ROWS = Reply(
    "How was First?\nHow was Second?",
    (
        (Button("Done ✓ · First", "stash:d:a"), Button("Didn't happen", "stash:h:a:20270212")),
        (Button("Done ✓ · Second", "stash:d:b"),),
    ),
)


def attached_handler(
    on_press: Callable[[CallbackPress], Awaitable[None]],
) -> Any:
    application = FakeTelegramApplication()
    TelegramAttachment(LateBoundOutbox(), on_press).attach(application)
    handler: Any = application.handlers[0]
    return handler


def test_a_reply_without_buttons_has_no_keyboard() -> None:
    # Execute
    keyboard = to_keyboard(PLAIN)

    # Assert
    assert keyboard is None


def test_a_reply_with_buttons_has_an_inline_keyboard_markup() -> None:
    # Execute
    keyboard = to_keyboard(WITH_BUTTONS)

    # Assert
    assert isinstance(keyboard, InlineKeyboardMarkup)


def test_the_keyboard_keeps_the_rows_and_button_labels() -> None:
    # Execute
    keyboard = to_keyboard(WITH_BUTTONS)

    # Assert
    assert keyboard is not None
    assert [[button.text for button in row] for row in keyboard.inline_keyboard] == [
        ["Type", "Stage"],
        ["Undo"],
    ]


def test_the_keyboard_keeps_the_callback_data_of_every_button() -> None:
    # Execute
    keyboard = to_keyboard(WITH_BUTTONS)

    # Assert
    assert keyboard is not None
    assert [[button.callback_data for button in row] for row in keyboard.inline_keyboard] == [
        ["stash:t:abc", "stash:s:abc"],
        ["stash:u:abc"],
    ]


def test_sending_passes_the_chat_id_and_text_to_the_bot() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).send("1001", PLAIN))

    # Assert
    assert [(sent.chat_id, sent.text) for sent in bot.sent] == [("1001", "Saved")]


def test_sending_a_reply_without_buttons_passes_no_reply_markup() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).send("1001", PLAIN))

    # Assert
    assert bot.sent[0].reply_markup is None


def test_sending_a_reply_with_buttons_passes_its_inline_keyboard() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).send("1001", WITH_BUTTONS))

    # Assert
    assert bot.sent[0].reply_markup == to_keyboard(WITH_BUTTONS)


def test_sending_calls_the_bot_with_keyword_arguments() -> None:
    # Setup
    bot = KeywordOnlyTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).send("1001", PLAIN))

    # Assert
    assert bot.calls == [("send", {"chat_id": "1001", "text": "Saved", "reply_markup": None})]


def test_editing_passes_the_message_id_as_an_integer() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).edit("1001", "55", PLAIN))

    # Assert
    assert [(edited.chat_id, edited.message_id, edited.text) for edited in bot.edited] == [
        ("1001", 55, "Saved")
    ]


def test_editing_a_reply_with_buttons_passes_its_inline_keyboard() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).edit("1001", "55", WITH_BUTTONS))

    # Assert
    assert bot.edited[0].reply_markup == to_keyboard(WITH_BUTTONS)


def test_editing_a_reply_without_buttons_passes_no_reply_markup() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).edit("1001", "55", PLAIN))

    # Assert
    assert bot.edited[0].reply_markup is None


def test_editing_calls_the_bot_with_keyword_arguments() -> None:
    # Setup
    bot = KeywordOnlyTelegramBot()

    # Execute
    asyncio.run(TelegramOutbox(bot).edit("1001", "55", PLAIN))

    # Assert
    assert bot.calls == [
        ("edit", {"text": "Saved", "chat_id": "1001", "message_id": 55, "reply_markup": None})
    ]


def test_editing_with_a_non_numeric_message_id_raises_value_error() -> None:
    # Setup
    outbox = TelegramOutbox(FakeTelegramBot())

    # Execute
    with pytest.raises(ValueError) as refusal:
        asyncio.run(outbox.edit("1001", "inline-7", PLAIN))

    # Assert
    assert "inline-7" in str(refusal.value)


def test_editing_with_a_non_numeric_message_id_never_reaches_the_bot() -> None:
    # Setup
    bot = FakeTelegramBot()

    # Execute
    with pytest.raises(ValueError):
        asyncio.run(TelegramOutbox(bot).edit("1001", "inline-7", PLAIN))

    # Assert
    assert bot.edited == []


def test_the_outbox_is_unavailable_before_the_attachment_is_attached() -> None:
    # Setup
    outbox = LateBoundOutbox()
    TelegramAttachment(outbox, PressLog([]))

    # Execute
    with pytest.raises(OutboxUnavailable) as refusal:
        asyncio.run(outbox.send("1001", PLAIN))

    # Assert
    assert refusal.type is OutboxUnavailable


def test_sending_after_attaching_reaches_the_application_bot() -> None:
    # Setup
    outbox = LateBoundOutbox()
    application = FakeTelegramApplication()
    TelegramAttachment(outbox, PressLog([])).attach(application)

    # Execute
    asyncio.run(outbox.send("1001", PLAIN))

    # Assert
    assert [(sent.chat_id, sent.text) for sent in application.bot.sent] == [("1001", "Saved")]


def test_editing_after_attaching_reaches_the_application_bot() -> None:
    # Setup
    outbox = LateBoundOutbox()
    application = FakeTelegramApplication()
    TelegramAttachment(outbox, PressLog([])).attach(application)

    # Execute
    asyncio.run(outbox.edit("1001", "55", PLAIN))

    # Assert
    assert [edited.message_id for edited in application.bot.edited] == [55]


def test_attaching_adds_exactly_one_callback_query_handler() -> None:
    # Setup
    application = FakeTelegramApplication()

    # Execute
    TelegramAttachment(LateBoundOutbox(), PressLog([])).attach(application)

    # Assert
    assert [type(handler) for handler in application.handlers] == [CallbackQueryHandler]


def test_the_handler_accepts_callback_data_of_a_stash_button() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([]), data="stash:t:abc")

    # Execute
    accepted = handler.check_update(update)

    # Assert
    assert accepted


def test_the_handler_rejects_callback_data_of_a_hermes_button() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([]), data="approve:xyz")

    # Execute
    accepted = handler.check_update(update)

    # Assert
    assert not accepted


def test_a_press_is_answered_before_it_is_handled() -> None:
    # Setup
    log: list[str] = []
    handler = attached_handler(PressLog(log))
    update = callback_update(AnsweringBot(log))

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert log == ["answer", "press"]


def test_a_press_is_handled_with_the_chat_message_and_data_of_the_query() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    update = callback_update(
        AnsweringBot([]), data="stash:t:abc", chat_id=1001, user_id=42, message_id=55
    )

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses == [CallbackPress(Chat("1001", "42"), "55", "stash:t:abc")]


def test_a_press_on_a_message_with_two_done_rows_carries_two_done_rows() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    keyboard = to_keyboard(TWO_DONE_ROWS)
    update = callback_update(AnsweringBot([]), data="stash:d:a", keyboard=keyboard)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses[0].done_rows == 2


def test_a_press_on_a_message_with_two_step_done_rows_carries_two_done_rows() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    keyboard = to_keyboard(
        Reply(
            "Two steps",
            ((Button("Done ✓ · Book", "stash:x:s1"),), (Button("Done ✓ · Pack", "stash:x:s2"),)),
        )
    )
    update = callback_update(AnsweringBot([]), data="stash:x:s1", keyboard=keyboard)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses[0].done_rows == 2


def test_a_press_on_a_menu_with_one_done_row_among_other_rows_carries_one_done_row() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    keyboard = to_keyboard(stage_menu(an_item_at(Stage.WANT_TO)))
    update = callback_update(AnsweringBot([]), data="stash:S:i1:doing", keyboard=keyboard)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses[0].done_rows == 1


def test_a_press_on_a_message_without_a_keyboard_carries_no_done_rows() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    update = callback_update(AnsweringBot([]), data="stash:d:a", keyboard=None)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses[0].done_rows == 0


def test_a_press_on_an_inaccessible_message_carries_no_done_rows() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    update = callback_update(AnsweringBot([]), data="stash:d:a", inaccessible=True)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses[0].done_rows == 0


def test_a_failing_press_does_not_raise_out_of_the_callback() -> None:
    # Setup
    handler = attached_handler(PressLog([], RuntimeError("boom")))
    update = callback_update(AnsweringBot([]))

    # Execute
    result = asyncio.run(handler.callback(update, None))

    # Assert
    assert result is None


def test_a_failing_press_is_logged_as_an_error_naming_the_chat() -> None:
    # Setup
    handler = attached_handler(PressLog([], RuntimeError("boom")))
    update = callback_update(AnsweringBot([]), chat_id=1001)

    # Execute
    with recording_logs(TELEGRAM_IO_LOGGER) as logs:
        asyncio.run(handler.callback(update, None))

    # Assert
    assert logs.entries() == [(logging.ERROR, "callback press failed for chat 1001")]


def test_a_query_without_a_message_is_answered() -> None:
    # Setup
    log: list[str] = []
    handler = attached_handler(PressLog(log))
    update = callback_update(AnsweringBot(log), with_message=False)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert log == ["answer"]


def test_a_query_without_data_is_answered_and_not_handled() -> None:
    # Setup
    log: list[str] = []
    handler = attached_handler(PressLog(log))
    update = callback_update(AnsweringBot(log), data=None)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert log == ["answer"]


def test_a_press_whose_acknowledgement_fails_is_still_handled() -> None:
    # Setup
    presses = PressLog([])
    handler = attached_handler(presses)
    update = callback_update(AnsweringBot([], NetworkError("down")), chat_id=1001, message_id=55)

    # Execute
    asyncio.run(handler.callback(update, None))

    # Assert
    assert presses.presses == [CallbackPress(Chat("1001", "42"), "55", "stash:t:abc")]


def test_a_failed_acknowledgement_warning_names_the_chat_and_the_exception_type() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([], NetworkError("down")), chat_id=1001)

    # Execute
    with recording_logs(TELEGRAM_IO_LOGGER) as logs:
        asyncio.run(handler.callback(update, None))

    # Assert
    assert logs.entries() == [
        (logging.WARNING, "could not acknowledge a button press in chat 1001: NetworkError")
    ]


def test_a_failed_acknowledgement_does_not_log_the_exception_message() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([], NetworkError("sk-leaked-value")), chat_id=1001)

    # Execute
    with recording_logs(TELEGRAM_IO_LOGGER) as logs:
        asyncio.run(handler.callback(update, None))

    # Assert
    assert not any("sk-leaked-value" in message for _, message in logs.entries())


def test_a_failed_acknowledgement_does_not_raise_out_of_the_callback() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([], NetworkError("down")), with_message=False)

    # Execute
    result = asyncio.run(handler.callback(update, None))

    # Assert
    assert result is None


def test_a_failed_acknowledgement_without_a_message_names_an_unknown_chat() -> None:
    # Setup
    handler = attached_handler(PressLog([]))
    update = callback_update(AnsweringBot([], NetworkError("down")), with_message=False)

    # Execute
    with recording_logs(TELEGRAM_IO_LOGGER) as logs:
        asyncio.run(handler.callback(update, None))

    # Assert
    assert logs.entries() == [
        (logging.WARNING, "could not acknowledge a button press in chat unknown: NetworkError")
    ]


def bound_to(method: Callable[..., Any], keywords: dict[str, Any]) -> set[str]:
    return set(inspect.signature(method).bind(None, **keywords).arguments)


def test_the_keywords_of_a_send_are_accepted_by_the_real_telegram_bot() -> None:
    # Setup
    bot = KeywordOnlyTelegramBot()
    asyncio.run(TelegramOutbox(bot).send("1001", WITH_BUTTONS))
    [(_, keywords)] = bot.calls

    # Execute
    bound = bound_to(Bot.send_message, keywords)

    # Assert
    assert bound == {"self", "chat_id", "text", "reply_markup"}


def test_the_keywords_of_an_edit_are_accepted_by_the_real_telegram_bot() -> None:
    # Setup
    bot = KeywordOnlyTelegramBot()
    asyncio.run(TelegramOutbox(bot).edit("1001", "55", WITH_BUTTONS))
    [(_, keywords)] = bot.calls

    # Execute
    bound = bound_to(Bot.edit_message_text, keywords)

    # Assert
    assert bound == {"self", "chat_id", "text", "message_id", "reply_markup"}


def test_attaching_the_same_application_again_adds_no_second_callback_query_handler() -> None:
    # Setup
    application = FakeTelegramApplication()
    attachment = TelegramAttachment(LateBoundOutbox(), PressLog([]))
    attachment.attach(application)

    # Execute
    attachment.attach(application)

    # Assert
    assert [type(handler) for handler in application.handlers] == [CallbackQueryHandler]


def test_attaching_a_new_application_adds_a_callback_query_handler_to_it() -> None:
    # Setup
    attachment = TelegramAttachment(LateBoundOutbox(), PressLog([]))
    attachment.attach(FakeTelegramApplication())
    reconnected = FakeTelegramApplication()

    # Execute
    attachment.attach(reconnected)

    # Assert
    assert [type(handler) for handler in reconnected.handlers] == [CallbackQueryHandler]


def test_sending_after_attaching_a_new_application_reaches_the_new_bot() -> None:
    # Setup
    outbox = LateBoundOutbox()
    attachment = TelegramAttachment(outbox, PressLog([]))
    attachment.attach(FakeTelegramApplication())
    reconnected = FakeTelegramApplication()
    attachment.attach(reconnected)

    # Execute
    asyncio.run(outbox.send("1001", PLAIN))

    # Assert
    assert [sent.text for sent in reconnected.bot.sent] == ["Saved"]


def test_sending_after_attaching_a_new_application_no_longer_reaches_the_old_bot() -> None:
    # Setup
    outbox = LateBoundOutbox()
    attachment = TelegramAttachment(outbox, PressLog([]))
    original = FakeTelegramApplication()
    attachment.attach(original)
    attachment.attach(FakeTelegramApplication())

    # Execute
    asyncio.run(outbox.send("1001", PLAIN))

    # Assert
    assert original.bot.sent == []


def test_the_keywords_of_a_file_are_accepted_by_the_real_telegram_bot() -> None:
    # Setup
    bot = KeywordOnlyTelegramBot()
    asyncio.run(TelegramOutbox(bot).send_file("1001", "library.html", b"<p>", "Your library"))
    [(_, keywords)] = bot.calls

    # Execute
    bound = bound_to(Bot.send_document, keywords)

    # Assert
    assert bound == {"self", "chat_id", "document", "filename", "caption"}
