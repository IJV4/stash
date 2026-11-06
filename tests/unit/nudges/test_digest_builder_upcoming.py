from datetime import date, datetime, timedelta

import pytest
from builders import in_los_angeles, stored
from digest_builders import DIGEST_AT, DIGEST_DAY, a_digest_builder, a_due_digest
from fakes.memory_store import MemoryStore
from nudge_builders import (
    a_planned_date_night,
    a_same_day_step,
    a_step_due_on,
    an_undated_date_night,
    stored_step,
)

from stash.domain import Stage
from stash.nudges.digest import UPCOMING_DAYS, UpcomingStep

LAST_DAY = DIGEST_DAY + timedelta(days=UPCOMING_DAYS)
ONE_DAY = timedelta(days=1)
WINDOW_EDGES = [
    (DIGEST_DAY - ONE_DAY, False),
    (DIGEST_DAY, True),
    (LAST_DAY, True),
    (LAST_DAY + ONE_DAY, False),
]
Entry = tuple[date, str, str | None]


def upcoming(store: MemoryStore, now: datetime = DIGEST_AT) -> list[Entry]:
    entries = a_digest_builder(store).build(a_due_digest(DIGEST_AT), now).sections.upcoming
    return [(e.on, e.item.id, e.step.id if isinstance(e, UpcomingStep) else None) for e in entries]


def stored_item_with_step_due_on(
    store: MemoryStore, day: date, item_id: str = "plan", step_id: str = "step", **item: object
) -> None:
    stored(store, an_undated_date_night(id=item_id, **item))
    stored_step(store, a_step_due_on(day, id=step_id, item_id=item_id))


@pytest.mark.parametrize(("day", "listed"), WINDOW_EDGES)
def test_a_dated_item_is_coming_up_from_today_through_fourteen_days_later(
    day: date, listed: bool
) -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="dated", date=day))

    # Execute
    entries = upcoming(store)

    # Assert
    assert bool(entries) is listed


@pytest.mark.parametrize(("day", "listed"), WINDOW_EDGES)
def test_a_step_is_coming_up_from_today_through_fourteen_days_later(
    day: date, listed: bool
) -> None:
    # Setup
    store = MemoryStore()
    stored_item_with_step_due_on(store, day)

    # Execute
    entries = upcoming(store)

    # Assert
    assert bool(entries) is listed


def test_a_dated_item_in_want_to_is_coming_up_too() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(id="maybe", date=DIGEST_DAY))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == [(DIGEST_DAY, "maybe", None)]


@pytest.mark.parametrize("stage", [Stage.DONE, Stage.DROPPED])
def test_a_closed_item_is_not_coming_up(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="closed", date=DIGEST_DAY, stage=stage))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


@pytest.mark.parametrize("stage", [Stage.DONE, Stage.DROPPED])
def test_a_step_of_a_closed_item_is_not_coming_up(stage: Stage) -> None:
    # Setup
    store = MemoryStore()
    stored_item_with_step_due_on(store, DIGEST_DAY, stage=stage)

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


def test_a_step_that_is_done_is_not_coming_up() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(id="plan"))
    stored_step(store, a_step_due_on(DIGEST_DAY, item_id="plan", done=True))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


def test_a_step_the_owner_has_not_confirmed_is_not_coming_up() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(id="plan"))
    stored_step(store, a_step_due_on(DIGEST_DAY, item_id="plan", confirmed=False))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


def test_a_step_is_listed_on_the_item_date_less_its_lead_days() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="dinner", date=DIGEST_DAY + 5 * ONE_DAY))
    stored_step(store, a_same_day_step(id="book", item_id="dinner", lead_days=2))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == [
        (DIGEST_DAY + 3 * ONE_DAY, "dinner", "book"),
        (DIGEST_DAY + 5 * ONE_DAY, "dinner", None),
    ]


def test_a_step_counted_from_an_undated_item_is_not_coming_up() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_undated_date_night(id="plan"))
    stored_step(store, a_same_day_step(item_id="plan", lead_days=2))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


def test_entries_are_ordered_by_date() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="later", date=DIGEST_DAY + 4 * ONE_DAY))
    stored(store, a_planned_date_night(id="sooner", date=DIGEST_DAY + 1 * ONE_DAY))
    stored_item_with_step_due_on(store, DIGEST_DAY + 2 * ONE_DAY, item_id="middle")

    # Execute
    entries = upcoming(store)

    # Assert
    assert [item_id for _, item_id, _ in entries] == ["sooner", "middle", "later"]


def test_on_the_same_date_the_items_come_before_the_steps() -> None:
    # Setup
    store = MemoryStore()
    day = DIGEST_DAY + 3 * ONE_DAY
    stored_item_with_step_due_on(store, day, item_id="aaa-step-first-by-id", step_id="early-step")
    stored(store, a_planned_date_night(id="zzz-item", date=day))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == [(day, "zzz-item", None), (day, "aaa-step-first-by-id", "early-step")]


def test_today_is_the_local_date_of_now() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="saturday", date=DIGEST_DAY - ONE_DAY))
    saturday_night_in_los_angeles = in_los_angeles(DIGEST_DAY - ONE_DAY, 23, 30)

    # Execute
    entries = upcoming(store, saturday_night_in_los_angeles)

    # Assert
    assert entries == [(DIGEST_DAY - ONE_DAY, "saturday", None)]


def test_the_window_is_counted_from_now_not_from_the_digest_instant() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_planned_date_night(id="before-now", date=DIGEST_DAY + ONE_DAY))
    stored(store, a_planned_date_night(id="after-the-window", date=LAST_DAY + 2 * ONE_DAY))

    # Execute
    entries = upcoming(store, DIGEST_AT + 2 * ONE_DAY)

    # Assert
    assert [item_id for _, item_id, _ in entries] == ["after-the-window"]
