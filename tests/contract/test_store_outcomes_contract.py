from datetime import timedelta

import pytest
from builders import (
    BASE,
    COMPLETED_ON,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    LATER,
    PLUS_FIVE,
    an_item_at,
    an_outcome,
    minutes_after,
    stored_item,
)
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import Stage
from stash.store import DuplicateOutcomeError, UnknownItemError

NEXT_DAY = COMPLETED_ON + timedelta(days=1)


@on_sqlite
def test_an_added_outcome_is_returned_by_get_outcome_with_takeaways_and_edited_at(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        outcome = an_outcome(takeaways=("Salt early", "Rest the meat"), edited_at=LATER)
        store.add_outcome(outcome)

        # Execute
        found = store.get_outcome(outcome.id)

        # Assert
        assert found == outcome


@on_sqlite
def test_an_outcome_without_rating_or_edit_round_trips_with_none(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        outcome = an_outcome(rating=None, takeaways=(), notes="")
        store.add_outcome(outcome)

        # Execute
        found = store.get_outcome(outcome.id)

        # Assert
        assert found == outcome


@on_sqlite
def test_an_outcome_with_non_utc_timestamps_reads_back_at_the_same_instants(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        recorded = BASE.astimezone(PLUS_FIVE)
        store.add_outcome(an_outcome(recorded_at=recorded, edited_at=recorded + timedelta(hours=1)))

        # Execute
        found = store.get_outcome("o1")

        # Assert
        assert found is not None
        assert (found.recorded_at, found.edited_at) == (BASE, BASE + timedelta(hours=1))


@on_sqlite
def test_an_outcome_edited_before_it_was_recorded_round_trips(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        outcome = an_outcome(recorded_at=LATER, edited_at=BASE)
        store.add_outcome(outcome)

        # Execute
        found = store.get_outcome(outcome.id)

        # Assert
        assert found == outcome


@on_sqlite
def test_get_outcome_of_an_unknown_id_returns_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.get_outcome("missing")

        # Assert
        assert found is None


@on_sqlite
def test_outcomes_for_an_unknown_item_is_empty(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.outcomes_for("missing")

        # Assert
        assert found == []


@on_sqlite
def test_outcomes_for_lists_only_the_outcomes_of_that_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.save_item(an_item_at(Stage.DONE, id="i2"))
        store.add_outcome(an_outcome(id="o1", item_id="i1"))
        store.add_outcome(an_outcome(id="o2", item_id="i2"))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o1"]


@on_sqlite
def test_adding_an_outcome_for_an_item_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Execute / Assert
    with open_store() as store, pytest.raises(UnknownItemError, match="i1"):
        store.add_outcome(an_outcome())


@on_sqlite
def test_adding_an_outcome_with_a_stored_id_raises_duplicate_outcome_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome())

        # Execute / Assert
        with pytest.raises(DuplicateOutcomeError, match="o1"):
            store.add_outcome(an_outcome(notes="Second try"))


@on_sqlite
def test_adding_an_outcome_with_a_stored_id_keeps_the_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome())
        with pytest.raises(DuplicateOutcomeError, match="o1"):
            store.add_outcome(an_outcome(notes="Second try"))

        # Execute
        found = store.get_outcome("o1")

        # Assert
        assert found == an_outcome()


@on_sqlite
def test_outcomes_for_lists_the_earlier_completion_day_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome(id="o1", completed_on=NEXT_DAY))
        store.add_outcome(an_outcome(id="o2", completed_on=COMPLETED_ON))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o2", "o1"]


@on_sqlite
def test_outcomes_for_lists_the_earlier_recording_first_on_the_same_day(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome(id="o1", recorded_at=minutes_after(5)))
        store.add_outcome(an_outcome(id="o2", recorded_at=minutes_after(1)))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o2", "o1"]


@on_sqlite
def test_outcomes_for_orders_recordings_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome(id="o1", recorded_at=BASE))
        store.add_outcome(an_outcome(id="o2", recorded_at=EARLIER_INSTANT_LATER_WALL_CLOCK))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o2", "o1"]


@on_sqlite
def test_outcomes_for_lists_the_lower_id_first_when_day_and_recording_instant_match(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome(id="o2"))
        store.add_outcome(an_outcome(id="o1"))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o1", "o2"]


@on_sqlite
def test_saving_an_edited_outcome_replaces_its_notes_and_takeaways(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        outcome = an_outcome()
        store.add_outcome(outcome)
        edited = outcome.with_notes("Better the second time", ("Less salt",), LATER)
        store.save_outcome(edited)

        # Execute
        found = store.get_outcome("o1")

        # Assert
        assert found == edited


@on_sqlite
def test_saving_an_edited_outcome_does_not_reorder_outcomes_for(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        older = an_outcome(id="o1", recorded_at=minutes_after(1))
        store.add_outcome(older)
        store.add_outcome(an_outcome(id="o2", recorded_at=minutes_after(2)))
        store.save_outcome(older.with_notes("Better", (), minutes_after(30)))

        # Execute
        found = store.outcomes_for("i1")

        # Assert
        assert [outcome.id for outcome in found] == ["o1", "o2"]


@on_sqlite
def test_saving_an_outcome_that_is_not_stored_adds_it(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.save_outcome(an_outcome())

        # Execute
        found = store.get_outcome("o1")

        # Assert
        assert found == an_outcome()


@on_sqlite
def test_saving_an_outcome_for_an_item_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Execute / Assert
    with open_store() as store, pytest.raises(UnknownItemError, match="i1"):
        store.save_outcome(an_outcome())


@on_sqlite
def test_deleting_an_item_removes_its_outcomes(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.add_outcome(an_outcome(id="o1"))
        store.add_outcome(an_outcome(id="o2"))
        store.delete_item("i1")

        # Execute
        found = (store.get_outcome("o1"), store.get_outcome("o2"), store.outcomes_for("i1"))

        # Assert
        assert found == (None, None, [])


@on_sqlite
def test_deleting_an_item_keeps_the_outcomes_of_other_items(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        store.save_item(an_item_at(Stage.DONE, id="i2"))
        store.add_outcome(an_outcome(id="o2", item_id="i2"))
        store.delete_item("i1")

        # Execute
        found = store.outcomes_for("i2")

        # Assert
        assert found == [an_outcome(id="o2", item_id="i2")]
