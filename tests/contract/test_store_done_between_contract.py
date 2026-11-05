import pytest
from builders import (
    an_outcome,
    days_after,
    minutes_after,
    stored_completion,
    titles,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import Stage


@all_stores
def test_done_between_lists_an_item_done_on_the_start_day(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", days_after(1))

        # Execute
        listed = store.done_between(days_after(1), days_after(4))

        # Assert
        assert titles(listed) == ["i1"]


@all_stores
def test_done_between_lists_an_item_done_on_the_end_day(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", days_after(4))

        # Execute
        listed = store.done_between(days_after(1), days_after(4))

        # Assert
        assert titles(listed) == ["i1"]


@all_stores
def test_done_between_leaves_out_items_done_only_outside_the_range(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "before", days_after(0))
        stored_completion(store, "after", days_after(5))

        # Execute
        listed = store.done_between(days_after(1), days_after(4))

        # Assert
        assert listed == []


@all_stores
def test_done_between_lists_an_item_with_several_outcomes_in_range_once(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "redone", days_after(1))
        store.add_outcome(an_outcome(id="o-again", item_id="redone", completed_on=days_after(2)))

        # Execute
        listed = store.done_between(days_after(1), days_after(4))

        # Assert
        assert titles(listed) == ["redone"]


@all_stores
def test_done_between_lists_the_later_completion_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "older", days_after(1))
        stored_completion(store, "newer", days_after(3))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["newer", "older"]


@all_stores
def test_done_between_ranks_an_item_by_its_latest_completion_inside_the_range(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "redone-later", days_after(1))
        store.add_outcome(
            an_outcome(id="o-later", item_id="redone-later", completed_on=days_after(9))
        )
        stored_completion(store, "once", days_after(3))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["once", "redone-later"]


@all_stores
def test_done_between_lists_the_later_recording_first_on_the_same_day(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "a-later", days_after(1), recorded_at=minutes_after(9))
        stored_completion(store, "b-earlier", days_after(1), recorded_at=minutes_after(1))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["a-later", "b-earlier"]


@all_stores
def test_done_between_lists_the_higher_item_id_first_when_day_and_recording_instant_match(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "a", days_after(1))
        stored_completion(store, "b", days_after(1))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["b", "a"]


@all_stores
def test_done_between_lists_an_item_that_was_reopened_since(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", days_after(1), stage=Stage.WANT_TO)

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["i1"]


@all_stores
def test_done_between_lists_an_item_that_was_not_kept(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", days_after(1), kept=False)

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["i1"]


@all_stores
def test_done_between_a_single_day_lists_the_items_done_that_day(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "that-day", days_after(2))
        stored_completion(store, "next-day", days_after(3))

        # Execute
        listed = store.done_between(days_after(2), days_after(2))

        # Assert
        assert titles(listed) == ["that-day"]


@all_stores
def test_done_between_with_a_start_after_the_end_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="start"):
        # Execute / Assert
        store.done_between(days_after(4), days_after(1))


@all_stores
def test_done_between_ranks_an_item_by_the_latest_of_its_outcomes_in_range(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "redone", days_after(1))
        store.add_outcome(an_outcome(id="o-again", item_id="redone", completed_on=days_after(3)))
        stored_completion(store, "once", days_after(2))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["redone", "once"]


@all_stores
def test_done_between_ranks_ties_by_item_id_whatever_the_outcome_ids_are(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "a", days_after(1))
        store.add_outcome(an_outcome(id="o-zzz", item_id="a", completed_on=days_after(1)))
        stored_completion(store, "b", days_after(1))
        store.add_outcome(an_outcome(id="o-low", item_id="b", completed_on=days_after(1)))

        # Execute
        listed = store.done_between(days_after(0), days_after(4))

        # Assert
        assert titles(listed) == ["b", "a"]
