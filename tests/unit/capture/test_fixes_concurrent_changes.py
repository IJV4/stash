import logging

import pytest
from capture_builders import store_with_filed_item
from capture_rig import CAPTURE_LOGGER, a_fix_handler
from fakes.busy_store import BusyStore
from fakes.vanishing_item_store import VanishingItemStore
from log_records import recording_logs

from stash.capture import gone
from stash.capture.replies import busy

FIXES = ["stash:T:c1:recipe", "stash:S:c1:doing"]


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_on_an_item_deleted_meanwhile_answers_gone(data: str) -> None:
    # Setup
    store = VanishingItemStore()
    store_with_filed_item(store)
    store.vanish_after_reading_item("c1")

    # Execute
    reply = a_fix_handler(store).apply(data)

    # Assert
    assert reply == gone()


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_on_an_item_deleted_meanwhile_does_not_bring_it_back(data: str) -> None:
    # Setup
    store = VanishingItemStore()
    store_with_filed_item(store)
    store.vanish_after_reading_item("c1")

    # Execute
    a_fix_handler(store).apply(data)

    # Assert
    assert store.get_item("c1") is None


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_on_an_item_deleted_meanwhile_is_logged_as_an_unknown_item(data: str) -> None:
    # Setup
    store = VanishingItemStore()
    store_with_filed_item(store)
    store.vanish_after_reading_item("c1")

    # Execute
    with recording_logs(CAPTURE_LOGGER) as recorder:
        a_fix_handler(store).apply(data)

    # Assert
    assert recorder.entries() == [(logging.INFO, "fix callback for unknown item c1")]


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_while_the_store_is_busy_answers_busy(data: str) -> None:
    # Setup
    store = BusyStore()
    store_with_filed_item(store)

    # Execute
    reply = a_fix_handler(store).apply(data)

    # Assert
    assert reply == busy()


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_while_the_store_is_busy_changes_nothing(data: str) -> None:
    # Setup
    store = BusyStore()
    _, item = store_with_filed_item(store)

    # Execute
    a_fix_handler(store).apply(data)

    # Assert
    assert store.get_item("c1") == item


@pytest.mark.parametrize("data", FIXES)
def test_a_fix_while_the_store_is_busy_is_logged_at_warning(data: str) -> None:
    # Setup
    store = BusyStore()
    store_with_filed_item(store)

    # Execute
    with recording_logs(CAPTURE_LOGGER) as recorder:
        a_fix_handler(store).apply(data)

    # Assert
    assert recorder.entries() == [(logging.WARNING, "fix callback while the stash was busy")]
