from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    EARLY_MORNING_PLUS_FIVE,
    LATE_EVENING_MINUS_FIVE,
    MICROSECOND,
    NAIVE,
    PLUS_FIVE,
    an_item_at,
    minutes_after,
    stored,
    stored_item,
    titles,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import Item, Stage
from stash.store import Store

CUTOFF = BASE + timedelta(days=30)
UTC_MIDNIGHT = datetime(2026, 11, 3, tzinfo=UTC)

AgeQuery = Callable[[Store, datetime, int], list[Item]]


@dataclass(frozen=True)
class AgedStage:
    stage: Stage
    query: AgeQuery


def wanted_older_than(store: Store, cutoff: datetime, limit: int) -> list[Item]:
    return store.want_to_older_than(cutoff, limit)


def doing_older_than(store: Store, cutoff: datetime, limit: int) -> list[Item]:
    return store.doing_older_than(cutoff, limit)


AGED_STAGES = (
    AgedStage(Stage.WANT_TO, wanted_older_than),
    AgedStage(Stage.DOING, doing_older_than),
)
both_age_queries = pytest.mark.parametrize(
    "aged", AGED_STAGES, ids=[aged.stage.value for aged in AGED_STAGES]
)
OTHER_STAGES = [(aged, stage) for aged in AGED_STAGES for stage in Stage if stage is not aged.stage]


def stored_updated_at(store: Store, aged: AgedStage, item_id: str, updated_at: datetime) -> Item:
    return stored_item(store, id=item_id, title=item_id, stage=aged.stage, updated_at=updated_at)


@all_stores
@both_age_queries
def test_an_age_query_leaves_out_an_item_updated_exactly_at_the_cutoff(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "at-cutoff", CUTOFF)

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert listed == []


@all_stores
@both_age_queries
def test_an_age_query_includes_an_item_updated_one_microsecond_before_the_cutoff(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "just-before", CUTOFF - MICROSECOND)

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert titles(listed) == ["just-before"]


@all_stores
@both_age_queries
def test_an_age_query_leaves_out_an_item_updated_after_the_cutoff(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "after", CUTOFF + MICROSECOND)

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert listed == []


@all_stores
@pytest.mark.parametrize(
    ("aged", "stage"),
    OTHER_STAGES,
    ids=[f"{aged.stage.value}-excludes-{stage.value}" for aged, stage in OTHER_STAGES],
)
def test_an_age_query_leaves_out_an_old_item_of_another_stage(
    open_store: StoreFactory, aged: AgedStage, stage: Stage
) -> None:
    # Setup
    with open_store() as store:
        stored(store, an_item_at(stage, id="other", title="other", updated_at=BASE))

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert listed == []


@all_stores
@both_age_queries
def test_an_age_query_lists_the_least_recently_updated_item_first(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "newest", minutes_after(9))
        stored_updated_at(store, aged, "oldest", minutes_after(1))
        stored_updated_at(store, aged, "middle", minutes_after(5))

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert titles(listed) == ["oldest", "middle", "newest"]


@all_stores
@both_age_queries
def test_an_age_query_breaks_a_tie_on_update_time_by_ascending_id(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "b", BASE)
        stored_updated_at(store, aged, "a", BASE)

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert titles(listed) == ["a", "b"]


@all_stores
@both_age_queries
def test_an_age_query_orders_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "utc-noon", BASE)
        stored_updated_at(store, aged, "plus-five", EARLIER_INSTANT_LATER_WALL_CLOCK)

        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert titles(listed) == ["plus-five", "utc-noon"]


@all_stores
@both_age_queries
def test_an_age_query_limit_keeps_the_oldest_items(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "third", minutes_after(3))
        stored_updated_at(store, aged, "first", minutes_after(1))
        stored_updated_at(store, aged, "second", minutes_after(2))

        # Execute
        listed = aged.query(store, CUTOFF, 2)

        # Assert
        assert titles(listed) == ["first", "second"]


@all_stores
@both_age_queries
def test_an_age_query_with_a_limit_of_zero_returns_nothing(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "old", BASE)

        # Execute
        listed = aged.query(store, CUTOFF, 0)

        # Assert
        assert listed == []


@all_stores
@both_age_queries
def test_an_age_query_with_a_negative_limit_raises_value_error(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="limit"):
        # Execute / Assert
        aged.query(store, CUTOFF, -1)


@all_stores
@both_age_queries
def test_an_age_query_with_a_naive_cutoff_raises_value_error(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="cutoff"):
        # Execute / Assert
        aged.query(store, NAIVE, 10)


@all_stores
@both_age_queries
def test_an_age_query_on_an_empty_store_returns_nothing(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        # Execute
        listed = aged.query(store, CUTOFF, 10)

        # Assert
        assert listed == []


@all_stores
@both_age_queries
def test_an_age_query_treats_a_late_evening_item_west_of_utc_as_after_a_utc_midnight_cutoff(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "west", LATE_EVENING_MINUS_FIVE)

        # Execute
        listed = aged.query(store, UTC_MIDNIGHT, 10)

        # Assert
        assert listed == []


@all_stores
@both_age_queries
def test_an_age_query_treats_an_early_morning_item_east_of_utc_as_before_a_utc_midnight_cutoff(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "east", EARLY_MORNING_PLUS_FIVE)

        # Execute
        listed = aged.query(store, UTC_MIDNIGHT, 10)

        # Assert
        assert titles(listed) == ["east"]


@all_stores
@both_age_queries
def test_an_age_query_accepts_a_cutoff_written_in_another_offset(
    open_store: StoreFactory, aged: AgedStage
) -> None:
    # Setup
    with open_store() as store:
        stored_updated_at(store, aged, "at-cutoff", UTC_MIDNIGHT)
        stored_updated_at(store, aged, "before-cutoff", UTC_MIDNIGHT - MICROSECOND)

        # Execute
        listed = aged.query(store, UTC_MIDNIGHT.astimezone(PLUS_FIVE), 10)

        # Assert
        assert titles(listed) == ["before-cutoff"]
