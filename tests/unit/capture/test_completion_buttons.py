import logging

from builders import BASE, fetched_outcome
from capture_builders import COMPLETED_OUTCOME_ID, a_store_with_a_completed_item
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle
from log_records import recording_logs

from stash.capture import gone
from stash.capture.callback_log import CallbackLog
from stash.capture.completion_buttons import CompletionButtons

LOGGER_NAME = "stash.capture.test_completion_buttons"
STORED_RATING = 4


def completion_buttons_over(store: MemoryStore) -> CompletionButtons:
    return CompletionButtons(
        store, a_lifecycle(store), CallbackLog(logging.getLogger(LOGGER_NAME)), lambda: BASE
    )


def test_a_rating_press_without_an_argument_answers_gone() -> None:
    # Setup
    buttons = completion_buttons_over(a_store_with_a_completed_item())

    # Execute
    reply = buttons.rate(COMPLETED_OUTCOME_ID, None)

    # Assert
    assert reply == gone()


def test_a_rating_press_without_an_argument_changes_nothing() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    completion_buttons_over(store).rate(COMPLETED_OUTCOME_ID, None)

    # Assert
    assert fetched_outcome(store, COMPLETED_OUTCOME_ID).rating == STORED_RATING


def test_a_rating_press_without_an_argument_is_logged_as_an_invalid_rating() -> None:
    # Setup
    buttons = completion_buttons_over(a_store_with_a_completed_item())

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.rate(COMPLETED_OUTCOME_ID, None)

    # Assert
    assert recorder.entries() == [
        (
            logging.WARNING,
            f"fix callback for outcome {COMPLETED_OUTCOME_ID} has an invalid rating None",
        )
    ]
