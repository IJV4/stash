from datetime import date, datetime, timedelta

import pytest
from builders import BASE, COMPLETED_ON, an_outcome, fetched_item, stored_item
from capture_builders import (
    COMPLETED_ITEM_ID,
    COMPLETED_OUTCOME_ID,
    COMPLETED_TITLE,
    a_store_with_a_completed_item,
    text_of,
)
from capture_rig import a_fix_handler
from fakes.memory_store import MemoryStore

from stash.capture import Reply, Reroute
from stash.capture.completion_buttons import DOUBLE_TAP_WINDOW
from stash.capture.completion_replies import done_reply
from stash.domain import Outcome, Stage
from stash.lifecycle.results import Completion

ONE_SECOND = timedelta(seconds=1)
ONE_DAY = timedelta(days=1)
DONE_PRESS = f"stash:d:{COMPLETED_ITEM_ID}"
SORTS_AFTER_THE_OLD_OUTCOME = COMPLETED_ON + ONE_DAY
SORTS_BEFORE_IT = COMPLETED_ON - ONE_DAY


def pressing_done(store: MemoryStore, now: datetime) -> Reply | Reroute:
    return a_fix_handler(store, lambda: now).apply(DONE_PRESS)


def fetched_outcome_of(store: MemoryStore) -> Outcome:
    [outcome] = store.outcomes_for(COMPLETED_ITEM_ID)
    return outcome


def first_tap_reply(store: MemoryStore, outcome: Outcome) -> Reply:
    return done_reply(Completion(fetched_item(store, COMPLETED_ITEM_ID), outcome, repeat=False))


def stored_outcome_recorded(store: MemoryStore, outcome_id: str, **overrides: object) -> Outcome:
    outcome = an_outcome(id=outcome_id, item_id=COMPLETED_ITEM_ID, **overrides)
    store.add_outcome(outcome)
    return outcome


def test_a_press_just_inside_the_window_records_no_second_outcome() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    pressing_done(store, BASE + DOUBLE_TAP_WINDOW - ONE_SECOND)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 1


def test_a_press_just_inside_the_window_answers_the_reply_the_first_tap_produced() -> None:
    # Setup
    store = a_store_with_a_completed_item()
    first = fetched_outcome_of(store)

    # Execute
    reply = pressing_done(store, BASE + DOUBLE_TAP_WINDOW - ONE_SECOND)

    # Assert
    assert reply == first_tap_reply(store, first)


def test_a_press_at_the_same_instant_as_the_latest_outcome_records_no_second_outcome() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    pressing_done(store, BASE)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 1


def test_a_press_exactly_one_window_after_the_latest_outcome_records_a_second_outcome() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    pressing_done(store, BASE + DOUBLE_TAP_WINDOW)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 2


def test_a_press_exactly_one_window_after_the_latest_outcome_answers_again() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = pressing_done(store, BASE + DOUBLE_TAP_WINDOW)

    # Assert
    assert text_of(reply).splitlines()[0] == f"🎉 Done: {COMPLETED_TITLE} (again)"


@pytest.mark.parametrize("later", [ONE_SECOND, ONE_DAY])
def test_a_press_after_the_window_records_a_second_outcome(later: timedelta) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    pressing_done(store, BASE + DOUBLE_TAP_WINDOW + later)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 2


@pytest.mark.parametrize("later", [ONE_SECOND, ONE_DAY])
def test_a_press_after_the_window_answers_again(later: timedelta) -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = pressing_done(store, BASE + DOUBLE_TAP_WINDOW + later)

    # Assert
    assert text_of(reply).splitlines()[0] == f"🎉 Done: {COMPLETED_TITLE} (again)"


def test_a_press_after_the_window_leaves_the_first_outcome_untouched() -> None:
    # Setup
    store = a_store_with_a_completed_item()
    first = fetched_outcome_of(store)

    # Execute
    pressing_done(store, BASE + DOUBLE_TAP_WINDOW)

    # Assert
    assert first in store.outcomes_for(COMPLETED_ITEM_ID)


@pytest.mark.parametrize("ahead", [ONE_SECOND, ONE_DAY])
def test_a_latest_outcome_in_the_future_of_the_clock_is_not_a_double_tap_and_records_a_second(
    ahead: timedelta,
) -> None:
    # Setup
    store = a_store_with_a_completed_item(recorded_at=BASE + ahead)

    # Execute
    pressing_done(store, BASE)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 2


@pytest.mark.parametrize("ahead", [ONE_SECOND, ONE_DAY])
def test_a_latest_outcome_in_the_future_of_the_clock_is_not_a_double_tap_and_answers_again(
    ahead: timedelta,
) -> None:
    # Setup
    store = a_store_with_a_completed_item(recorded_at=BASE + ahead)

    # Execute
    reply = pressing_done(store, BASE)

    # Assert
    assert text_of(reply).splitlines()[0] == f"🎉 Done: {COMPLETED_TITLE} (again)"


@pytest.mark.parametrize("recent_completed_on", [SORTS_AFTER_THE_OLD_OUTCOME, SORTS_BEFORE_IT])
def test_the_most_recently_recorded_outcome_decides_whether_a_press_is_a_double_tap(
    recent_completed_on: date,
) -> None:
    # Setup
    now = BASE + ONE_DAY
    store = a_store_with_a_completed_item()
    stored_outcome_recorded(
        store, "o-recent", recorded_at=now - ONE_SECOND, completed_on=recent_completed_on
    )

    # Execute
    pressing_done(store, now)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 2


@pytest.mark.parametrize("recent_completed_on", [SORTS_AFTER_THE_OLD_OUTCOME, SORTS_BEFORE_IT])
def test_a_double_tap_answers_the_reply_of_the_most_recently_recorded_outcome(
    recent_completed_on: date,
) -> None:
    # Setup
    now = BASE + ONE_DAY
    store = a_store_with_a_completed_item()
    recent = stored_outcome_recorded(
        store, "o-recent", recorded_at=now - ONE_SECOND, completed_on=recent_completed_on
    )

    # Execute
    reply = pressing_done(store, now)

    # Assert
    assert reply == first_tap_reply(store, recent)


def test_a_press_within_the_window_leaves_every_outcome_as_it_was() -> None:
    # Setup
    store = a_store_with_a_completed_item()
    before = store.outcomes_for(COMPLETED_ITEM_ID)

    # Execute
    pressing_done(store, BASE + ONE_SECOND)

    # Assert
    assert store.outcomes_for(COMPLETED_ITEM_ID) == before


def test_a_press_within_the_window_leaves_the_item_as_it_was() -> None:
    # Setup
    store = a_store_with_a_completed_item()
    before = fetched_item(store, COMPLETED_ITEM_ID)

    # Execute
    pressing_done(store, BASE + ONE_SECOND)

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID) == before


def test_pressing_done_on_an_item_reopened_since_a_recent_outcome_records_a_new_outcome() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id=COMPLETED_ITEM_ID, stage=Stage.DOING)
    stored_outcome_recorded(store, COMPLETED_OUTCOME_ID, recorded_at=BASE)

    # Execute
    pressing_done(store, BASE + ONE_SECOND)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 2


def test_pressing_done_on_an_item_reopened_since_a_recent_outcome_completes_it_again() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id=COMPLETED_ITEM_ID, stage=Stage.DOING)
    stored_outcome_recorded(store, COMPLETED_OUTCOME_ID, recorded_at=BASE)

    # Execute
    pressing_done(store, BASE + ONE_SECOND)

    # Assert
    assert fetched_item(store, COMPLETED_ITEM_ID).stage is Stage.DONE


def test_pressing_done_on_a_done_item_without_any_outcome_records_one() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id=COMPLETED_ITEM_ID, stage=Stage.DONE)

    # Execute
    pressing_done(store, BASE)

    # Assert
    assert len(store.outcomes_for(COMPLETED_ITEM_ID)) == 1
