import logging

from builders import stored_item
from fakes.busy_store import BusyStore
from fakes.changing_item_store import ChangingItemStore
from fakes.failing_completion_store import FailingCompletionStore
from fakes.failing_read_store import FailingReadStore
from fakes.failing_save_store import FailingSaveStore
from log_records import recording_logs
from tool_rig import (
    answer_of,
    lifecycle_tools_over,
    store_snapshot,
)

from stash.domain import Stage

LOGGER = "stash.hermes_adapter.lifecycle_tools"
COULD_NOT_UPDATE = {"error": "the stash could not be updated"}
COULD_NOT_READ = {"error": "the stash could not be read"}


def test_a_store_that_fails_while_writing_answers_could_not_be_updated() -> None:
    # Setup
    store = FailingSaveStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    store.fail_next_save = True

    # Execute
    answer = answer_of(lifecycle_tools_over(store).set_stage({"item_id": "w1", "stage": "doing"}))

    # Assert
    assert answer == COULD_NOT_UPDATE


def test_a_store_that_fails_while_completing_answers_could_not_be_updated() -> None:
    # Setup
    store = FailingCompletionStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    store.fail_next_completion = True

    # Execute
    answer = answer_of(lifecycle_tools_over(store).complete({"item_id": "w1"}))

    # Assert
    assert answer == COULD_NOT_UPDATE


def test_a_failure_while_writing_is_logged_as_one_error() -> None:
    # Setup
    store = FailingSaveStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    store.fail_next_save = True
    tools = lifecycle_tools_over(store)

    # Execute
    with recording_logs(LOGGER) as logs:
        tools.set_stage({"item_id": "w1", "stage": "doing"})

    # Assert
    assert [level for level, _ in logs.entries()] == [logging.ERROR]


def test_a_store_that_fails_while_reading_answers_could_not_be_read() -> None:
    # Setup
    store = FailingReadStore()

    # Execute
    answer = answer_of(lifecycle_tools_over(store).get({"item_id": "w1"}))

    # Assert
    assert answer == COULD_NOT_READ


def test_a_library_that_fails_to_load_answers_could_not_be_read() -> None:
    # Execute
    answer = answer_of(lifecycle_tools_over(FailingReadStore()).library({}))

    # Assert
    assert answer == COULD_NOT_READ


def test_a_failure_while_reading_is_logged_as_one_error() -> None:
    # Setup
    tools = lifecycle_tools_over(FailingReadStore())

    # Execute
    with recording_logs(LOGGER) as logs:
        tools.get({"item_id": "w1"})

    # Assert
    assert [level for level, _ in logs.entries()] == [logging.ERROR]


def test_a_failed_write_leaves_the_store_as_it_was() -> None:
    # Setup
    store = FailingCompletionStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    before = store_snapshot(store)
    store.fail_next_completion = True

    # Execute
    lifecycle_tools_over(store).complete({"item_id": "w1", "rating": 4})

    # Assert
    assert store_snapshot(store) == before


def test_a_tool_on_an_item_changed_meanwhile_answers_the_item_changed_text() -> None:
    # Setup
    store = ChangingItemStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)
    store.change_after_reading_item("w1")

    # Execute
    answer = answer_of(lifecycle_tools_over(store).set_stage({"item_id": "w1", "stage": "doing"}))

    # Assert
    assert answer == {"error": "item 'w1' changed meanwhile; read it again and try again"}


def test_a_tool_while_the_store_is_busy_answers_the_stash_busy_text() -> None:
    # Setup
    store = BusyStore()
    stored_item(store, id="w1", stage=Stage.WANT_TO)

    # Execute
    answer = answer_of(lifecycle_tools_over(store).set_stage({"item_id": "w1", "stage": "doing"}))

    # Assert
    assert answer == {"error": "the stash is busy with another change; try again in a moment"}
