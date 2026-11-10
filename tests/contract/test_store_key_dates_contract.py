from datetime import date

import pytest
from fakes.store_factories import StoreFactory, on_sqlite
from people_builders import a_key_date, stored_person

from stash.domain import KeyDate
from stash.store import UnknownPersonError

YEAR_END_WINDOW = (date(2026, 12, 20), date(2027, 1, 10))


def key_date_ids(key_dates: list[KeyDate]) -> list[str]:
    return [key_date.id for key_date in key_dates]


def occurrence_ids(store_result: list[tuple[KeyDate, date]]) -> list[tuple[str, date]]:
    return [(key_date.id, occurrence) for key_date, occurrence in store_result]


@on_sqlite
def test_a_saved_key_date_reads_back_whole(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        key_date = a_key_date(year=None)
        store.save_key_date(key_date)

        # Execute
        found = store.key_dates_for("p1")

        # Assert
        assert found == [key_date]


@on_sqlite
def test_a_persons_key_dates_are_listed_by_month_then_day_then_id(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="k1", month=6, day=1))
        store.save_key_date(a_key_date(id="k2", month=1, day=20))
        store.save_key_date(a_key_date(id="k3", month=1, day=5))

        # Execute
        found = store.key_dates_for("p1")

        # Assert
        assert key_date_ids(found) == ["k3", "k2", "k1"]


@on_sqlite
def test_key_dates_are_listed_only_for_their_own_person(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())
        stored_person(store, id="p2", name="Bruno", aliases=())
        store.save_key_date(a_key_date(id="k1", person_id="p1"))
        store.save_key_date(a_key_date(id="k2", person_id="p2"))

        # Execute
        found = store.key_dates_for("p2")

        # Assert
        assert key_date_ids(found) == ["k2"]


@on_sqlite
def test_saving_a_key_date_for_an_unknown_person_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(UnknownPersonError):
        # Execute / Assert
        store.save_key_date(a_key_date(person_id="missing"))


@on_sqlite
def test_deleting_a_person_removes_their_key_dates(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date())
        store.delete_person("p1")

        # Execute
        found = store.key_dates_between(date(2026, 1, 1), date(2026, 12, 31))

        # Assert
        assert found == []


@on_sqlite
def test_deleting_a_person_leaves_other_peoples_key_dates(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store, id="p1", name="Ana", aliases=())
        stored_person(store, id="p2", name="Bruno", aliases=())
        store.save_key_date(a_key_date(id="k1", person_id="p1"))
        store.save_key_date(a_key_date(id="k2", person_id="p2"))
        store.delete_person("p1")

        # Execute
        found = store.key_dates_for("p2")

        # Assert
        assert key_date_ids(found) == ["k2"]


@on_sqlite
def test_a_window_across_a_year_end_returns_dates_on_both_sides(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="k1", month=12, day=30))
        store.save_key_date(a_key_date(id="k2", month=1, day=3))
        store.save_key_date(a_key_date(id="k3", month=6, day=1))

        # Execute
        found = store.key_dates_between(*YEAR_END_WINDOW)

        # Assert
        assert occurrence_ids(found) == [("k1", date(2026, 12, 30)), ("k2", date(2027, 1, 3))]


@on_sqlite
def test_a_window_includes_dates_on_its_first_and_last_day(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="k1", month=3, day=1))
        store.save_key_date(a_key_date(id="k2", month=3, day=10))

        # Execute
        found = store.key_dates_between(date(2026, 3, 1), date(2026, 3, 10))

        # Assert
        assert key_date_ids([key_date for key_date, _ in found]) == ["k1", "k2"]


@on_sqlite
def test_occurrences_are_ordered_by_day_then_key_date_id(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="kb", month=3, day=5))
        store.save_key_date(a_key_date(id="ka", month=3, day=5))
        store.save_key_date(a_key_date(id="kc", month=3, day=2))

        # Execute
        found = store.key_dates_between(date(2026, 3, 1), date(2026, 3, 31))

        # Assert
        assert key_date_ids([key_date for key_date, _ in found]) == ["kc", "ka", "kb"]


@on_sqlite
def test_a_february_29_date_occurs_on_february_28_in_a_common_year(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="k1", month=2, day=29, year=None))

        # Execute
        found = store.key_dates_between(date(2027, 2, 1), date(2027, 3, 31))

        # Assert
        assert occurrence_ids(found) == [("k1", date(2027, 2, 28))]


@on_sqlite
def test_a_window_longer_than_a_year_lists_each_key_date_once(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_person(store)
        store.save_key_date(a_key_date(id="k1", month=3, day=14))

        # Execute
        found = store.key_dates_between(date(2026, 1, 1), date(2028, 12, 31))

        # Assert
        assert occurrence_ids(found) == [("k1", date(2026, 3, 14))]


@on_sqlite
def test_a_window_that_ends_before_it_starts_is_refused(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError, match="start must not be after end"):
        # Execute / Assert
        store.key_dates_between(date(2026, 3, 2), date(2026, 3, 1))
