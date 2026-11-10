import datetime as dt

import pytest
from builders import LATER
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.faulty_store import FaultyStore, busy_store

from stash.capture import gone, stage_menu
from stash.capture.replies import busy
from stash.store import UnknownItemError

A_DATE = dt.date(2026, 11, 14)


def test_choosing_a_type_that_does_not_exist_answers_gone_and_changes_nothing() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:T:c1:spaceship")

    # Assert
    assert (reply, store.get_item("c1")) == (gone(), item)


@pytest.mark.parametrize("stage", ["planned", "done", "nonsense"])
def test_choosing_a_stage_the_menu_did_not_offer_answers_the_menu_again(stage: str) -> None:
    # Setup
    store, item = store_with_filed_item(date=None)

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply(f"stash:S:c1:{stage}")

    # Assert
    assert reply == stage_menu(item)


def test_choosing_a_stage_the_menu_did_not_offer_changes_nothing() -> None:
    # Setup
    store, item = store_with_filed_item(date=None)

    # Execute
    a_fix_handler(store, lambda: LATER).apply("stash:S:c1:planned")

    # Assert
    assert store.get_item("c1") == item


def test_pressing_a_type_while_the_store_is_busy_answers_busy() -> None:
    # Setup
    store, _ = store_with_filed_item(busy_store())

    # Execute
    reply = a_fix_handler(store).apply("stash:T:c1:recipe")

    # Assert
    assert reply == busy()


def test_pressing_a_type_for_an_item_another_process_deleted_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item(FaultyStore(fail_on={"update_item": UnknownItemError("c1")}))

    # Execute
    reply = a_fix_handler(store).apply("stash:T:c1:recipe")

    # Assert
    assert reply == gone()
