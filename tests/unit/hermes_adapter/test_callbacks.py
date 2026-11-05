import asyncio
import logging
import threading

from builders import a_capture
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.asked_assistant import AskedAssistant
from fakes.edit_recording_outbox import EditFailed, EditRecordingOutbox
from fakes.scripted_fixes import ScriptedFixes
from log_records import recording_logs

from stash.capture import type_menu
from stash.hermes_adapter.callbacks import CallbackPress, FixCallbacks
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.owners import Owners

LOGGER = "stash.hermes_adapter.callbacks"
OWNER_ID = "42"
STRANGER_ID = "99"
CHAT_ID = "7001"
MESSAGE_ID = "55"
TYPE_MENU_DATA = "stash:t:c1"
QUESTION_DATA = "stash:q:c1"
PRESS_RETURNED = "returned"


class Harness:
    def __init__(
        self, apply_failure: Exception | None = None, edit_failure: Exception | None = None
    ) -> None:
        self.store, self.item = store_with_filed_item()
        self.fixes = ScriptedFixes(a_fix_handler(self.store), apply_failure)
        self.outbox = EditRecordingOutbox(edit_failure)
        self.assistant = AskedAssistant()
        self.callbacks = FixCallbacks(
            self.fixes, Owners.parse(OWNER_ID), self.outbox, self.assistant
        )

    def press(self, data: str, user_id: str = OWNER_ID) -> str:
        press = CallbackPress(Chat(CHAT_ID, user_id), MESSAGE_ID, data)
        asyncio.run(self.callbacks.on_press(press))
        return PRESS_RETURNED


def test_an_owner_pressing_a_menu_button_edits_the_message_with_the_menu() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(TYPE_MENU_DATA)

    # Assert
    assert harness.outbox.edits == [(CHAT_ID, MESSAGE_ID, type_menu(harness.item))]


def test_pressing_that_was_a_question_hands_the_text_to_the_assistant_for_that_chat() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(QUESTION_DATA)

    # Assert
    assert harness.assistant.asked == [(a_capture().text, Chat(CHAT_ID, OWNER_ID))]


def test_pressing_that_was_a_question_edits_nothing() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(QUESTION_DATA)

    # Assert
    assert harness.outbox.edits == []


def test_a_menu_button_asks_the_assistant_nothing() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(TYPE_MENU_DATA)

    # Assert
    assert harness.assistant.asked == []


def test_the_fix_is_applied_on_a_worker_thread() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(TYPE_MENU_DATA)

    # Assert
    assert [t != threading.get_ident() for t in harness.fixes.threads] == [True]


def test_the_fix_is_applied_to_the_pressed_data() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(TYPE_MENU_DATA)

    # Assert
    assert harness.fixes.applied == [TYPE_MENU_DATA]


def test_a_press_from_a_non_owner_applies_no_fix() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(QUESTION_DATA, user_id=STRANGER_ID)

    # Assert
    assert harness.fixes.applied == []


def test_a_press_from_a_non_owner_edits_nothing_and_asks_nothing() -> None:
    # Setup
    harness = Harness()

    # Execute
    harness.press(QUESTION_DATA, user_id=STRANGER_ID)

    # Assert
    assert (harness.outbox.edits, harness.assistant.asked) == ([], [])


def test_a_press_from_a_non_owner_is_logged_at_info_with_the_chat_only() -> None:
    # Setup
    harness = Harness()

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.press(QUESTION_DATA, user_id=STRANGER_ID)

    # Assert
    assert logs.entries() == [
        (logging.INFO, "ignoring a button press from a non-owner in chat 7001")
    ]


def test_a_failing_edit_is_swallowed() -> None:
    # Setup
    harness = Harness(edit_failure=EditFailed("message is gone"))

    # Execute
    outcome = harness.press(TYPE_MENU_DATA)

    # Assert
    assert outcome == PRESS_RETURNED


def test_a_failing_edit_is_logged_with_the_chat_and_message_ids() -> None:
    # Setup
    harness = Harness(edit_failure=EditFailed("message is gone"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.press(TYPE_MENU_DATA)

    # Assert
    assert logs.entries() == [
        (logging.ERROR, "could not handle a button press on message 55 in chat 7001")
    ]


def test_a_failing_fix_is_swallowed() -> None:
    # Setup
    harness = Harness(apply_failure=RuntimeError("store is locked"))

    # Execute
    outcome = harness.press(TYPE_MENU_DATA)

    # Assert
    assert outcome == PRESS_RETURNED


def test_a_failing_fix_is_logged_with_the_chat_and_message_ids() -> None:
    # Setup
    harness = Harness(apply_failure=RuntimeError("store is locked"))

    # Execute
    with recording_logs(LOGGER) as logs:
        harness.press(TYPE_MENU_DATA)

    # Assert
    assert logs.entries() == [
        (logging.ERROR, "could not handle a button press on message 55 in chat 7001")
    ]


def test_a_failing_fix_edits_nothing() -> None:
    # Setup
    harness = Harness(apply_failure=RuntimeError("store is locked"))

    # Execute
    harness.press(TYPE_MENU_DATA)

    # Assert
    assert harness.outbox.edits == []
