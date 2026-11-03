import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    PLUS_FIVE,
    a_capture,
    a_source,
    minutes_after,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import CaptureStatus
from stash.store import UnknownCaptureError


@all_stores
def test_added_capture_is_returned_by_get_capture(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        capture = a_capture()
        store.add_capture(capture)

        # Execute
        found = store.get_capture(capture.id)

        # Assert
        assert found == capture


@all_stores
def test_adding_a_new_capture_returns_true(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        added = store.add_capture(a_capture())

        # Assert
        assert added is True


@all_stores
def test_adding_a_capture_with_an_already_seen_source_returns_false(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="c1"))

        # Execute
        added = store.add_capture(a_capture(id="c2"))

        # Assert
        assert added is False


@all_stores
def test_a_duplicate_source_leaves_exactly_one_pending_capture(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="c1"))
        store.add_capture(a_capture(id="c2"))

        # Execute
        pending = store.pending_captures()

        # Assert
        assert [capture.id for capture in pending] == ["c1"]


@all_stores
def test_a_duplicate_source_writes_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="c1"))
        store.add_capture(a_capture(id="c2"))

        # Execute
        found = store.get_capture("c2")

        # Assert
        assert found is None


@all_stores
def test_adding_the_very_same_capture_twice_returns_false(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute
        added = store.add_capture(a_capture())

        # Assert
        assert added is False


@all_stores
def test_adding_a_capture_with_an_existing_id_from_another_source_raises_value_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="c1", source=a_source("m1")))

        # Execute / Assert
        with pytest.raises(ValueError):
            store.add_capture(a_capture(id="c1", source=a_source("m2")))


@all_stores
def test_a_capture_with_a_non_utc_received_at_reads_back_at_the_same_instant(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        capture = a_capture(received_at=BASE.astimezone(PLUS_FIVE))
        store.add_capture(capture)

        # Execute
        found = store.get_capture(capture.id)

        # Assert
        assert found is not None
        assert found.received_at == BASE


@all_stores
def test_get_capture_of_an_unknown_id_returns_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.get_capture("missing")

        # Assert
        assert found is None


@all_stores
def test_changing_a_capture_status_is_visible_through_get_capture(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute
        store.set_capture_status("c1", CaptureStatus.FILED)

        # Assert
        assert store.get_capture("c1") == a_capture(status=CaptureStatus.FILED)


@all_stores
def test_changing_a_capture_status_removes_it_from_pending(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute
        store.set_capture_status("c1", CaptureStatus.FILED)

        # Assert
        assert store.pending_captures() == []


@all_stores
def test_setting_the_status_of_an_unknown_capture_raises_unknown_capture_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(UnknownCaptureError):
        # Execute / Assert
        store.set_capture_status("missing", CaptureStatus.FILED)


@all_stores
def test_pending_captures_come_oldest_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(
            a_capture(id="late", source=a_source("m1"), received_at=minutes_after(10))
        )
        store.add_capture(
            a_capture(id="early", source=a_source("m2"), received_at=minutes_after(1))
        )
        store.add_capture(
            a_capture(id="middle", source=a_source("m3"), received_at=minutes_after(5))
        )

        # Execute
        pending = store.pending_captures()

        # Assert
        assert [capture.id for capture in pending] == ["early", "middle", "late"]


@all_stores
def test_pending_captures_received_at_the_same_instant_come_in_id_order(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="b", source=a_source("m1")))
        store.add_capture(a_capture(id="a", source=a_source("m2")))

        # Execute
        pending = store.pending_captures()

        # Assert
        assert [capture.id for capture in pending] == ["a", "b"]


@all_stores
def test_pending_captures_order_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture(id="utc", source=a_source("m1"), received_at=BASE))
        store.add_capture(
            a_capture(
                id="plus-five", source=a_source("m2"), received_at=EARLIER_INSTANT_LATER_WALL_CLOCK
            )
        )

        # Execute
        pending = store.pending_captures()

        # Assert
        assert [capture.id for capture in pending] == ["plus-five", "utc"]


@all_stores
def test_a_stored_setting_is_returned(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.put_setting("gpu.manual_off_until", "2026-11-02T16:00:00+00:00")

        # Execute
        value = store.get_setting("gpu.manual_off_until")

        # Assert
        assert value == "2026-11-02T16:00:00+00:00"


@all_stores
def test_putting_a_setting_again_overwrites_it(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.put_setting("key", "old")
        store.put_setting("key", "new")

        # Execute
        value = store.get_setting("key")

        # Assert
        assert value == "new"


@all_stores
def test_a_missing_setting_is_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        value = store.get_setting("missing")

        # Assert
        assert value is None
