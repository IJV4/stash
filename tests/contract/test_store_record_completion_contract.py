from dataclasses import replace

import pytest
from builders import (
    LATER,
    a_capture,
    an_item_at,
    an_outcome,
    minutes_after,
    stored_item,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import Item, Outcome, Stage
from stash.store import DuplicateOutcomeError, Store, UnknownCaptureError, UnknownItemError


def refused_completion(
    store: Store, item: Item, outcome: Outcome, error: type[Exception], match: str
) -> None:
    with pytest.raises(error, match=match):
        store.record_completion(item, outcome)


@all_stores
def test_record_completion_stores_the_completed_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute
        store.record_completion(item.completed(LATER), an_outcome())

        # Assert
        assert store.get_item("i1") == item.completed(LATER)


@all_stores
def test_record_completion_stores_the_outcome(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute
        store.record_completion(item.completed(LATER), an_outcome())

        # Assert
        assert store.outcomes_for("i1") == [an_outcome()]


@all_stores
def test_record_completion_of_an_item_that_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = an_item_at(Stage.DOING)

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="i1"):
            store.record_completion(item.completed(LATER), an_outcome())


@all_stores
def test_record_completion_of_an_item_that_is_not_stored_writes_neither_half(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = an_item_at(Stage.DOING)

        # Execute
        refused_completion(store, item.completed(LATER), an_outcome(), UnknownItemError, "i1")

        # Assert
        assert (store.get_item("i1"), store.outcomes_for("i1")) == (None, [])


@all_stores
def test_record_completion_with_a_stored_outcome_id_raises_duplicate_outcome_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        store.add_outcome(an_outcome())

        # Execute / Assert
        with pytest.raises(DuplicateOutcomeError, match="o1"):
            store.record_completion(item.completed(LATER), an_outcome(notes="Again"))


@all_stores
def test_record_completion_with_a_stored_outcome_id_leaves_the_item_as_it_was(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        store.add_outcome(an_outcome())

        # Execute
        refused_completion(
            store, item.completed(LATER), an_outcome(notes="Again"), DuplicateOutcomeError, "o1"
        )

        # Assert
        assert (store.get_item("i1"), store.outcomes_for("i1")) == (item, [an_outcome()])


@all_stores
def test_record_completion_with_an_outcome_of_another_item_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute / Assert
        with pytest.raises(ValueError, match="i2"):
            store.record_completion(item.completed(LATER), an_outcome(item_id="i2"))


@all_stores
def test_record_completion_with_an_outcome_of_another_item_writes_neither_half(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        store.save_item(an_item_at(Stage.DOING, id="i2"))

        # Execute
        refused_completion(store, item.completed(LATER), an_outcome(item_id="i2"), ValueError, "i2")

        # Assert
        found = (store.get_item("i1"), store.outcomes_for("i1"), store.outcomes_for("i2"))
        assert found == (item, [], [])


@all_stores
def test_record_completion_of_an_item_whose_parent_is_not_stored_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.record_completion(replace(item.completed(LATER), parent_id="p1"), an_outcome())


@all_stores
def test_record_completion_of_an_item_whose_parent_is_not_stored_writes_neither_half(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute
        refused_completion(
            store,
            replace(item.completed(LATER), parent_id="p1"),
            an_outcome(),
            UnknownItemError,
            "p1",
        )

        # Assert
        assert (store.get_item("i1"), store.outcomes_for("i1")) == (item, [])


@all_stores
def test_record_completion_of_an_item_moved_to_an_unknown_capture_raises_unknown_capture_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute / Assert
        with pytest.raises(UnknownCaptureError, match="c9"):
            store.record_completion(replace(item.completed(LATER), capture_id="c9"), an_outcome())


@all_stores
def test_record_completion_of_an_item_moved_to_an_unknown_capture_writes_neither_half(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)

        # Execute
        refused_completion(
            store,
            replace(item.completed(LATER), capture_id="c9"),
            an_outcome(),
            UnknownCaptureError,
            "c9",
        )

        # Assert
        assert (store.get_item("i1"), store.outcomes_for("i1")) == (item, [])


@all_stores
def test_record_completion_reports_a_missing_parent_before_a_stored_outcome_id(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        store.add_outcome(an_outcome())

        # Execute / Assert
        with pytest.raises(UnknownItemError, match="p1"):
            store.record_completion(
                replace(item.completed(LATER), parent_id="p1"), an_outcome(notes="Again")
            )


@all_stores
def test_completing_a_reopened_item_again_lists_both_outcomes(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        done = item.completed(LATER)
        store.record_completion(done, an_outcome(id="o1"))
        reopened = done.reopened(minutes_after(300))
        store.save_item(reopened)

        # Execute
        store.record_completion(
            reopened.completed(minutes_after(400)),
            an_outcome(id="o2", recorded_at=minutes_after(400)),
        )

        # Assert
        assert [outcome.id for outcome in store.outcomes_for("i1")] == ["o1", "o2"]


@all_stores
def test_completing_a_reopened_item_again_leaves_the_first_outcome_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DOING)
        done = item.completed(LATER)
        store.record_completion(done, an_outcome(id="o1"))
        reopened = done.reopened(minutes_after(300))
        store.save_item(reopened)

        # Execute
        store.record_completion(
            reopened.completed(minutes_after(400)), an_outcome(id="o2", notes="Second time")
        )

        # Assert
        assert store.get_outcome("o1") == an_outcome(id="o1")
