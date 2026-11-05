import datetime as dt

import pytest
from builders import BASE, LATER
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler

from stash.capture import confirmation, gone, stage_menu
from stash.domain import ItemType, Stage

A_DATE = dt.date(2026, 11, 14)


def test_choosing_a_type_answers_the_updated_confirmation() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:T:c1:recipe")

    # Assert
    assert reply == confirmation(item.retyped(ItemType.RECIPE, LATER), unsure=False)


def test_choosing_a_type_persists_it_and_stamps_the_update_time() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    a_fix_handler(store, lambda: LATER).apply("stash:T:c1:recipe")

    # Assert
    assert store.get_item("c1") == item.retyped(ItemType.RECIPE, LATER)


def test_choosing_a_type_leaves_the_creation_time_alone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    a_fix_handler(store, lambda: LATER).apply("stash:T:c1:recipe")

    # Assert
    item = store.get_item("c1")
    assert item is not None and item.created_at == BASE


def test_choosing_a_type_that_does_not_exist_answers_gone_and_changes_nothing() -> None:
    # Setup
    store, item = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:T:c1:spaceship")

    # Assert
    assert (reply, store.get_item("c1")) == (gone(), item)


def test_choosing_a_type_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:T:unknown:recipe")

    # Assert
    assert reply == gone()


def test_choosing_an_offered_stage_answers_the_updated_confirmation() -> None:
    # Setup
    store, item = store_with_filed_item(stage=Stage.INBOX)

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:S:c1:doing")

    # Assert
    assert reply == confirmation(item.moved_to(Stage.DOING, LATER), unsure=False)


def test_choosing_an_offered_stage_persists_it_and_stamps_the_update_time() -> None:
    # Setup
    store, item = store_with_filed_item(stage=Stage.INBOX)

    # Execute
    a_fix_handler(store, lambda: LATER).apply("stash:S:c1:doing")

    # Assert
    assert store.get_item("c1") == item.moved_to(Stage.DOING, LATER)


def test_choosing_planned_for_an_item_with_a_date_is_accepted() -> None:
    # Setup
    store, item = store_with_filed_item(date=A_DATE)

    # Execute
    a_fix_handler(store, lambda: LATER).apply("stash:S:c1:planned")

    # Assert
    assert store.get_item("c1") == item.moved_to(Stage.PLANNED, LATER)


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


def test_choosing_a_stage_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply("stash:S:unknown:doing")

    # Assert
    assert reply == gone()
