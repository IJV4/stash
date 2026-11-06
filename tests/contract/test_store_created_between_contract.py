from datetime import UTC, datetime, timedelta

import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    EARLY_MORNING_PLUS_FIVE,
    LATE_EVENING_MINUS_FIVE,
    MICROSECOND,
    MINUS_FIVE,
    NAIVE,
    PLUS_FIVE,
    SPRING_FORWARD_DAY,
    an_item_at,
    in_los_angeles,
    stored,
    stored_item,
    titles,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import Stage

START = BASE
END = BASE + timedelta(days=1)
UTC_DAY_START = datetime(2026, 11, 3, tzinfo=UTC)
UTC_DAY_END = datetime(2026, 11, 4, tzinfo=UTC)
SPRING_FORWARD_DAY_START = in_los_angeles(SPRING_FORWARD_DAY)
SPRING_FORWARD_DAY_END = in_los_angeles(SPRING_FORWARD_DAY + timedelta(days=1))


@all_stores
def test_created_between_includes_an_item_created_exactly_at_the_start(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="at-start", title="at-start", created_at=START)

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert titles(listed) == ["at-start"]


@all_stores
def test_created_between_leaves_out_an_item_created_one_microsecond_before_the_start(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="before", title="before", created_at=START - MICROSECOND)

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_created_between_leaves_out_an_item_created_exactly_at_the_end(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="at-end", title="at-end", created_at=END)

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_created_between_includes_an_item_created_one_microsecond_before_the_end(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(
            store, id="just-before-end", title="just-before-end", created_at=END - MICROSECOND
        )

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert titles(listed) == ["just-before-end"]


@all_stores
def test_created_between_an_empty_window_returns_nothing_even_at_that_instant(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="at-instant", title="at-instant", created_at=START)

        # Execute
        listed = store.created_between(START, START)

        # Assert
        assert listed == []


@all_stores
def test_created_between_lists_the_newest_item_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="middle", title="middle", created_at=START + timedelta(hours=2))
        stored_item(store, id="oldest", title="oldest", created_at=START + timedelta(hours=1))
        stored_item(store, id="newest", title="newest", created_at=START + timedelta(hours=3))

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert titles(listed) == ["newest", "middle", "oldest"]


@all_stores
def test_created_between_breaks_a_tie_on_creation_time_by_descending_id(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="a", title="a", created_at=START)
        stored_item(store, id="b", title="b", created_at=START)

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert titles(listed) == ["b", "a"]


@all_stores
def test_created_between_orders_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="utc-noon", title="utc-noon", created_at=BASE)
        stored_item(
            store, id="plus-five", title="plus-five", created_at=EARLIER_INSTANT_LATER_WALL_CLOCK
        )

        # Execute
        listed = store.created_between(BASE - timedelta(days=1), END)

        # Assert
        assert titles(listed) == ["utc-noon", "plus-five"]


@all_stores
@pytest.mark.parametrize("stage", list(Stage), ids=lambda stage: stage.value)
def test_created_between_returns_an_item_of_every_stage(
    open_store: StoreFactory, stage: Stage
) -> None:
    # Setup
    with open_store() as store:
        stored(store, an_item_at(stage, id="any", title="any", created_at=START))

        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert titles(listed) == ["any"]


@all_stores
def test_created_between_on_an_empty_store_returns_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        listed = store.created_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_created_between_with_a_start_after_the_end_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="start"):
        # Execute / Assert
        store.created_between(END, START)


@all_stores
def test_created_between_with_a_naive_start_raises_value_error(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="start"):
        # Execute / Assert
        store.created_between(NAIVE, END)


@all_stores
def test_created_between_with_a_naive_end_raises_value_error(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="end"):
        # Execute / Assert
        store.created_between(START, NAIVE)


@all_stores
def test_created_between_includes_a_late_evening_item_west_of_utc_in_the_next_utc_day(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="west", title="west", created_at=LATE_EVENING_MINUS_FIVE)

        # Execute
        listed = store.created_between(UTC_DAY_START, UTC_DAY_END)

        # Assert
        assert titles(listed) == ["west"]


@all_stores
def test_created_between_leaves_out_an_early_morning_item_east_of_utc_from_the_same_utc_day(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="east", title="east", created_at=EARLY_MORNING_PLUS_FIVE)

        # Execute
        listed = store.created_between(UTC_DAY_START, UTC_DAY_END)

        # Assert
        assert listed == []


@all_stores
def test_created_between_accepts_bounds_written_in_another_offset(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="at-start", title="at-start", created_at=UTC_DAY_START)
        stored_item(store, id="at-end", title="at-end", created_at=UTC_DAY_END)

        # Execute
        listed = store.created_between(
            UTC_DAY_START.astimezone(PLUS_FIVE), UTC_DAY_END.astimezone(MINUS_FIVE)
        )

        # Assert
        assert titles(listed) == ["at-start"]


@all_stores
def test_created_between_a_twenty_three_hour_local_day_catches_exactly_the_items_created_inside_it(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(
            store,
            id="last-minute-before",
            title="last-minute-before",
            created_at=datetime(2027, 3, 14, 7, 59, 59, tzinfo=UTC),
        )
        stored_item(
            store,
            id="first-instant",
            title="first-instant",
            created_at=datetime(2027, 3, 14, 8, 0, tzinfo=UTC),
        )
        stored_item(
            store,
            id="last-minute",
            title="last-minute",
            created_at=datetime(2027, 3, 15, 6, 59, 59, tzinfo=UTC),
        )
        stored_item(
            store,
            id="first-of-next-day",
            title="first-of-next-day",
            created_at=datetime(2027, 3, 15, 7, 0, tzinfo=UTC),
        )

        # Execute
        listed = store.created_between(SPRING_FORWARD_DAY_START, SPRING_FORWARD_DAY_END)

        # Assert
        assert titles(listed) == ["last-minute", "first-instant"]
