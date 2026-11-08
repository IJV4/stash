import datetime as dt

import pytest
from builders import LATER
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler

from stash.capture import gone, stage_menu

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
