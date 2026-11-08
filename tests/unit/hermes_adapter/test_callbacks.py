import asyncio
import logging

from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.asked_assistant import AskedAssistant
from fakes.edit_recording_outbox import EditFailed, EditRecordingOutbox
from fakes.scripted_fixes import ScriptedFixes
from log_records import recording_logs

from stash.hermes_adapter.callbacks import CallbackPress, FixCallbacks
from stash.hermes_adapter.events import Chat
from stash.hermes_adapter.owners import Owners

LOGGER = "stash.hermes_adapter.callbacks"
OWNER_ID = "42"
STRANGER_ID = "99"
CHAT_ID = "7001"
MESSAGE_ID = "55"
TYPE_MENU_DATA = "stash:t:c1"
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

    def press(self, data: str, user_id: str = OWNER_ID, done_rows: int = 0) -> str:
        press = CallbackPress(Chat(CHAT_ID, user_id), MESSAGE_ID, data, done_rows)
        asyncio.run(self.callbacks.on_press(press))
        return PRESS_RETURNED


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
