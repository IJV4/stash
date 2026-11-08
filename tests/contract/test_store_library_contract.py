import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    an_outcome,
    days_after,
    minutes_after,
    stored_completion,
    stored_item,
    titles,
)
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import ItemType, Stage
from stash.store.port import DEFAULT_PAGE_SIZE


@on_sqlite
def test_library_lists_a_kept_completed_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        item = stored_completion(store, "i1", kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert listed == [item]


@on_sqlite
def test_library_leaves_out_an_item_that_was_not_kept(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", kept=False)

        # Execute
        listed = store.library()

        # Assert
        assert listed == []


@on_sqlite
def test_library_leaves_out_a_dropped_item_even_when_it_is_kept(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", kept=True, stage=Stage.DROPPED)

        # Execute
        listed = store.library()

        # Assert
        assert listed == []


@on_sqlite
def test_library_keeps_listing_a_kept_item_that_was_reopened(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "i1", kept=True, stage=Stage.WANT_TO)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["i1"]


@on_sqlite
def test_library_by_type_lists_only_kept_items_of_that_type(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "recipe-kept", kept=True, item_type=ItemType.RECIPE)
        stored_completion(store, "recipe-loose", kept=False, item_type=ItemType.RECIPE)
        stored_completion(store, "place-kept", kept=True, item_type=ItemType.PLACE)

        # Execute
        listed = store.library(ItemType.RECIPE)

        # Assert
        assert titles(listed) == ["recipe-kept"]


@on_sqlite
def test_library_lists_the_later_completion_day_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "older", days_after(0), kept=True)
        stored_completion(store, "newer", days_after(3), kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["newer", "older"]


@on_sqlite
def test_library_lists_the_later_recording_first_on_the_same_day(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "a-later", recorded_at=minutes_after(9), kept=True)
        stored_completion(store, "b-earlier", recorded_at=minutes_after(1), kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["a-later", "b-earlier"]


@on_sqlite
def test_library_orders_recordings_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(
            store, "wall-clock-later", recorded_at=EARLIER_INSTANT_LATER_WALL_CLOCK, kept=True
        )
        stored_completion(store, "instant-later", recorded_at=BASE, kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["instant-later", "wall-clock-later"]


@on_sqlite
def test_library_lists_the_higher_outcome_id_first_when_day_and_recording_instant_match(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "a", kept=True)
        stored_completion(store, "b", kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["b", "a"]


@on_sqlite
def test_library_ranks_an_item_by_its_latest_completion(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "redone", days_after(0), kept=True)
        store.add_outcome(an_outcome(id="o-again", item_id="redone", completed_on=days_after(5)))
        stored_completion(store, "once", days_after(3), kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["redone", "once"]


@on_sqlite
def test_library_lists_an_item_with_several_outcomes_once(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_completion(store, "redone", days_after(0), kept=True)
        store.add_outcome(an_outcome(id="o-again", item_id="redone", completed_on=days_after(5)))

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["redone"]


@on_sqlite
def test_library_lists_kept_items_never_completed_after_completed_ones(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="never", title="never", kept=True, created_at=minutes_after(60))
        stored_completion(store, "done", kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["done", "never"]


@on_sqlite
def test_library_lists_kept_items_never_completed_newest_created_first(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        for minute, name in enumerate(["first", "second", "third"]):
            stored_item(store, id=name, title=name, kept=True, created_at=minutes_after(minute))

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["third", "second", "first"]


@on_sqlite
def test_library_lists_the_higher_item_id_first_among_never_completed_items_created_together(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        for name in ["a", "b"]:
            stored_item(store, id=name, title=name, kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert titles(listed) == ["b", "a"]


@on_sqlite
def test_library_limit_caps_the_number_returned(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        for number in range(3):
            stored_completion(store, f"i{number}", days_after(number), kept=True)

        # Execute
        listed = store.library(limit=2)

        # Assert
        assert titles(listed) == ["i2", "i1"]


@on_sqlite
def test_library_offset_skips_the_most_recent(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        for number in range(3):
            stored_completion(store, f"i{number}", days_after(number), kept=True)

        # Execute
        listed = store.library(limit=1, offset=1)

        # Assert
        assert titles(listed) == ["i1"]


@on_sqlite
def test_library_returns_twenty_by_default(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        for number in range(DEFAULT_PAGE_SIZE + 1):
            stored_completion(store, f"i{number:02}", days_after(number), kept=True)

        # Execute
        listed = store.library()

        # Assert
        assert len(listed) == DEFAULT_PAGE_SIZE


@on_sqlite
@pytest.mark.parametrize(("limit", "offset"), [(-1, 0), (20, -1)], ids=["limit", "offset"])
def test_library_with_a_negative_limit_or_offset_raises_value_error(
    open_store: StoreFactory, limit: int, offset: int
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError):
        # Execute / Assert
        store.library(limit=limit, offset=offset)
