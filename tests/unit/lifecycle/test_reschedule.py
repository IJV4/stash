from datetime import timedelta

from builders import LATER, PLANNED_FOR, an_item_at, fetched_item, stored
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage


def test_rescheduling_a_planned_item_moves_its_date_and_keeps_it_planned() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.PLANNED))
    new_date = PLANNED_FOR + timedelta(days=7)

    # Execute
    moved = a_lifecycle(store, clock=lambda: LATER).reschedule("i1", new_date)

    # Assert
    assert (moved.stage, moved.date, moved.updated_at) == (Stage.PLANNED, new_date, LATER)


def test_a_rescheduled_item_is_stored_with_its_new_date() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.PLANNED))

    # Execute
    moved = a_lifecycle(store).reschedule("i1", PLANNED_FOR + timedelta(days=7))

    # Assert
    assert fetched_item(store, "i1") == moved


def test_clearing_the_date_of_a_planned_item_moves_it_to_want_to() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.PLANNED))

    # Execute
    cleared = a_lifecycle(store).reschedule("i1", None)

    # Assert
    assert (cleared.stage, cleared.date) == (Stage.WANT_TO, None)
