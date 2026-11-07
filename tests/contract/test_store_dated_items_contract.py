from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    an_outcome,
    minutes_after,
    stored_item,
    titles,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import Item, Stage
from stash.store import Store

START = date(2026, 11, 10)
END = date(2026, 11, 14)
MIDDLE = date(2026, 11, 12)
DAY_BEFORE = START - timedelta(days=1)
DAY_AFTER = END + timedelta(days=1)

DatedQuery = Callable[[Store, date, date], list[Item]]


def every_stage(store: Store, start: date, end: date) -> list[Item]:
    return store.items_dated_between(start, end)


def planned_awaiting_outcome(store: Store, start: date, end: date) -> list[Item]:
    return store.planned_awaiting_outcome_dated_between(start, end)


both_dated_queries = pytest.mark.parametrize(
    "query",
    [every_stage, planned_awaiting_outcome],
    ids=["items_dated", "planned_awaiting_outcome"],
)


def planned_on(store: Store, item_id: str, day: date, **overrides: Any) -> Item:
    return stored_item(store, id=item_id, title=item_id, stage=Stage.PLANNED, date=day, **overrides)


@all_stores
@both_dated_queries
def test_a_dated_query_includes_an_item_dated_on_the_start_day(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "on-start", START)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["on-start"]


@all_stores
@both_dated_queries
def test_a_dated_query_includes_an_item_dated_on_the_end_day(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "on-end", END)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["on-end"]


@all_stores
@both_dated_queries
def test_a_dated_query_leaves_out_an_item_dated_the_day_before_the_start(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "before", DAY_BEFORE)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert listed == []


@all_stores
@both_dated_queries
def test_a_dated_query_leaves_out_an_item_dated_the_day_after_the_end(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "after", DAY_AFTER)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert listed == []


@all_stores
@both_dated_queries
def test_a_dated_query_over_a_single_day_returns_the_items_of_that_day(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "the-day", MIDDLE)
        planned_on(store, "next-day", MIDDLE + timedelta(days=1))

        # Execute
        listed = query(store, MIDDLE, MIDDLE)

        # Assert
        assert titles(listed) == ["the-day"]


@all_stores
@both_dated_queries
def test_a_dated_query_lists_the_earlier_date_first(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "late", END, created_at=minutes_after(1))
        planned_on(store, "early", START, created_at=minutes_after(9))
        planned_on(store, "middle", MIDDLE, created_at=minutes_after(5))

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["early", "middle", "late"]


@all_stores
@both_dated_queries
def test_a_dated_query_lists_the_earlier_created_item_first_within_a_date(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "a-newer", MIDDLE, created_at=minutes_after(9))
        planned_on(store, "b-older", MIDDLE, created_at=minutes_after(1))

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["b-older", "a-newer"]


@all_stores
@both_dated_queries
def test_a_dated_query_orders_creation_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "utc-noon", MIDDLE, created_at=BASE)
        planned_on(store, "plus-five", MIDDLE, created_at=EARLIER_INSTANT_LATER_WALL_CLOCK)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["plus-five", "utc-noon"]


@all_stores
@both_dated_queries
def test_a_dated_query_breaks_a_tie_on_date_and_creation_by_ascending_id(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "b", MIDDLE)
        planned_on(store, "a", MIDDLE)

        # Execute
        listed = query(store, START, END)

        # Assert
        assert titles(listed) == ["a", "b"]


@all_stores
@both_dated_queries
def test_a_dated_query_on_an_empty_store_returns_nothing(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store:
        # Execute
        listed = query(store, START, END)

        # Assert
        assert listed == []


@all_stores
@both_dated_queries
def test_a_dated_query_with_a_start_after_the_end_raises_value_error(
    open_store: StoreFactory, query: DatedQuery
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="start"):
        # Execute / Assert
        query(store, END, START)


@all_stores
@pytest.mark.parametrize("stage", list(Stage), ids=lambda stage: stage.value)
def test_items_dated_between_returns_an_item_of_every_stage(
    open_store: StoreFactory, stage: Stage
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="any", title="any", stage=stage, date=MIDDLE)

        # Execute
        listed = store.items_dated_between(START, END)

        # Assert
        assert titles(listed) == ["any"]


@all_stores
def test_items_dated_between_never_returns_an_item_without_a_date(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="undated", title="undated", stage=Stage.WANT_TO, date=None)

        # Execute
        listed = store.items_dated_between(date.min, date.max)

        # Assert
        assert listed == []


@all_stores
def test_items_dated_between_returns_an_item_that_already_has_an_outcome(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "i1", MIDDLE)
        store.add_outcome(an_outcome(item_id="i1", completed_on=MIDDLE))

        # Execute
        listed = store.items_dated_between(START, END)

        # Assert
        assert titles(listed) == ["i1"]


@all_stores
@pytest.mark.parametrize(
    "stage", [stage for stage in Stage if stage is not Stage.PLANNED], ids=lambda stage: stage.value
)
def test_planned_awaiting_outcome_leaves_out_a_dated_item_of_another_stage(
    open_store: StoreFactory, stage: Stage
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, id="other", title="other", stage=stage, date=MIDDLE)

        # Execute
        listed = store.planned_awaiting_outcome_dated_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_planned_awaiting_outcome_leaves_out_a_planned_item_that_has_an_outcome(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "i1", MIDDLE)
        store.add_outcome(an_outcome(item_id="i1", completed_on=MIDDLE))

        # Execute
        listed = store.planned_awaiting_outcome_dated_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_planned_awaiting_outcome_leaves_out_a_planned_item_with_several_outcomes(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "i1", MIDDLE)
        store.add_outcome(an_outcome(id="o1", item_id="i1", completed_on=MIDDLE))
        store.add_outcome(an_outcome(id="o2", item_id="i1", completed_on=MIDDLE))

        # Execute
        listed = store.planned_awaiting_outcome_dated_between(START, END)

        # Assert
        assert listed == []


@all_stores
def test_planned_awaiting_outcome_keeps_a_repeat_item_whose_outcome_is_from_an_earlier_date(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "repeat", MIDDLE)
        store.add_outcome(an_outcome(item_id="repeat", completed_on=DAY_BEFORE))

        # Execute
        listed = store.planned_awaiting_outcome_dated_between(START, END)

        # Assert
        assert titles(listed) == ["repeat"]


@all_stores
def test_planned_awaiting_outcome_keeps_a_planned_item_whose_neighbour_has_an_outcome(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        planned_on(store, "with-outcome", MIDDLE)
        planned_on(store, "without-outcome", MIDDLE)
        store.add_outcome(an_outcome(item_id="with-outcome", completed_on=MIDDLE))

        # Execute
        listed = store.planned_awaiting_outcome_dated_between(START, END)

        # Assert
        assert titles(listed) == ["without-outcome"]
