from datetime import date

import pytest
from builders import an_item_at, fetched_item, stored
from clocks import EVENING_IN_LOS_ANGELES
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import LifecycleRefused

DAY_AFTER_TOMORROW = date(2026, 11, 4)


def a_doing_item_store() -> FreshStore:
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))
    return store


def test_completing_two_days_after_the_local_today_is_refused_naming_the_date() -> None:
    # Setup
    lifecycle = a_lifecycle(a_doing_item_store(), clock=lambda: EVENING_IN_LOS_ANGELES)

    # Execute
    with pytest.raises(LifecycleRefused, match="completed_on 2026-11-04 is after tomorrow"):
        lifecycle.complete("i1", on=DAY_AFTER_TOMORROW)


def test_a_completion_dated_in_the_future_leaves_the_item_and_outcomes_unchanged() -> None:
    # Setup
    store = a_doing_item_store()
    lifecycle = a_lifecycle(store, clock=lambda: EVENING_IN_LOS_ANGELES)

    # Execute
    with pytest.raises(LifecycleRefused):
        lifecycle.complete("i1", on=DAY_AFTER_TOMORROW)

    # Assert
    assert (fetched_item(store, "i1").stage, store.outcomes_for("i1")) == (Stage.DOING, [])
