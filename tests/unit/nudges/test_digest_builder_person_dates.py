from datetime import date, timedelta

import pytest
from builders import stored
from digest_builders import DIGEST_AT, DIGEST_DAY, building
from fakes.store_factories import FreshStore
from nudge_builders import (
    a_planned_date_night,
    a_step_due_on,
    an_undated_date_night,
    stored_step,
)
from people_builders import a_key_date, stored_person

from stash.nudges.digest import UPCOMING_DAYS, UpcomingItem, UpcomingPersonDate, UpcomingStep

LAST_DAY = DIGEST_DAY + timedelta(days=UPCOMING_DAYS)
ONE_DAY = timedelta(days=1)
WINDOW_EDGES = [
    (DIGEST_DAY - ONE_DAY, False),
    (DIGEST_DAY, True),
    (LAST_DAY, True),
    (LAST_DAY + ONE_DAY, False),
]


def person_dates_coming_up(store: FreshStore) -> list[UpcomingPersonDate]:
    return [e for e in building(store, DIGEST_AT).upcoming if isinstance(e, UpcomingPersonDate)]


@pytest.mark.parametrize(("day", "listed"), WINDOW_EDGES)
def test_a_key_date_is_coming_up_from_today_through_fourteen_days_later(
    day: date, listed: bool
) -> None:
    # Setup
    store = FreshStore()
    ana = stored_person(store)
    store.save_key_date(a_key_date(person_id=ana.id, month=day.month, day=day.day))

    # Execute
    entries = person_dates_coming_up(store)

    # Assert
    assert [entry.on for entry in entries] == ([day] if listed else [])


def test_a_coming_up_key_date_carries_the_person_the_key_date_and_the_occurrence() -> None:
    # Setup
    store = FreshStore()
    ana = stored_person(store)
    key_date = a_key_date(person_id=ana.id, month=2, day=10)
    store.save_key_date(key_date)

    # Execute
    entries = person_dates_coming_up(store)

    # Assert
    assert entries == [UpcomingPersonDate(date(2027, 2, 10), ana, key_date)]


def test_on_the_same_day_a_dated_item_comes_before_a_step_which_comes_before_a_key_date() -> None:
    # Setup
    store = FreshStore()
    day = DIGEST_DAY + ONE_DAY
    ana = stored_person(store)
    store.save_key_date(a_key_date(person_id=ana.id, month=day.month, day=day.day))
    stored(store, an_undated_date_night(id="plan"))
    stored_step(store, a_step_due_on(day, id="step", item_id="plan"))
    stored(store, a_planned_date_night(id="dated", date=day))

    # Execute
    entries = building(store, DIGEST_AT).upcoming

    # Assert
    assert [type(entry) for entry in entries] == [UpcomingItem, UpcomingStep, UpcomingPersonDate]
