from datetime import date
from typing import Any

from builders import PLANNED_FOR, an_item, fetched_item, stored
from fakes.store_factories import FreshStore
from tool_rig import a_tool_store, answer_of, lifecycle_tools_over

from stash.domain import Stage

PLANNED_ITEM = "pl1"
NEW_DATE = date(2026, 11, 21)


def a_store_with_a_planned_item() -> FreshStore:
    store = a_tool_store()
    stored(store, an_item(id=PLANNED_ITEM, stage=Stage.PLANNED, date=PLANNED_FOR))
    return store


def dated(arguments: dict[str, Any], store: FreshStore) -> dict[str, Any]:
    return answer_of(lifecycle_tools_over(store).set_date({"item_id": PLANNED_ITEM, **arguments}))


def test_set_date_moves_a_planned_item_to_the_new_date() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    answer = dated({"date": NEW_DATE.isoformat()}, store)

    # Assert
    assert (answer["item"]["stage"], answer["item"]["date"]) == ("planned", "2026-11-21")


def test_set_date_saves_the_new_date_in_the_store() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    dated({"date": NEW_DATE.isoformat()}, store)

    # Assert
    assert fetched_item(store, PLANNED_ITEM).date == NEW_DATE


def test_set_date_with_a_null_date_moves_a_planned_item_back_to_want_to() -> None:
    # Setup
    store = a_store_with_a_planned_item()

    # Execute
    answer = dated({"date": None}, store)

    # Assert
    assert (answer["item"]["stage"], answer["item"]["date"]) == ("want_to", None)
