from dataclasses import replace
from datetime import date, timedelta

import pytest
from builders import (
    BASE,
    EARLIER_INSTANT_LATER_WALL_CLOCK,
    PLUS_FIVE,
    a_capture,
    an_item,
    minutes_after,
    titles,
)
from fakes.store_factories import StoreFactory, all_stores

from stash.domain import ItemType, Stage
from stash.store import Store, UnknownCaptureError


def seed_three_items(store: Store) -> None:
    store.add_capture(a_capture())
    for minute in range(3):
        store.save_item(
            an_item(id=f"i{minute}", title=f"Item {minute}", created_at=minutes_after(minute))
        )


@all_stores
def test_a_saved_item_is_returned_by_get_item(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = an_item()
        store.save_item(item)

        # Execute
        found = store.get_item(item.id)

        # Assert
        assert found == item


@all_stores
def test_get_item_of_an_unknown_id_returns_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.get_item("missing")

        # Assert
        assert found is None


@all_stores
def test_an_item_with_every_field_populated_round_trips_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = replace(
            an_item(note="Go with Aiko, bring cash"),
            stage=Stage.PLANNED,
            source_url="https://example.com/ramen?lang=en&ref=1",
            details={"city": "Tokyo", "price": "¥1,200"},
            tags=("food", "ramen"),
            people=("Aiko", "Ben"),
            date=date(2026, 12, 24),
        )
        store.save_item(item)

        # Execute
        found = store.get_item(item.id)

        # Assert
        assert found == item


@all_stores
def test_non_ascii_text_in_details_tags_and_people_survives_a_round_trip(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = replace(
            an_item(),
            details={"店": "ラーメン一郎", "café": "crème brûlée"},
            tags=("寿司", "café"),
            people=("Zoë",),
        )
        store.save_item(item)

        # Execute
        found = store.get_item(item.id)

        # Assert
        assert found == item


@all_stores
def test_an_item_without_source_url_or_date_round_trips_with_none(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item())

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is not None
        assert (found.source_url, found.date) == (None, None)


@all_stores
def test_an_item_with_non_utc_timestamps_reads_back_at_the_same_instants(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        created = BASE.astimezone(PLUS_FIVE)
        store.save_item(
            replace(an_item(created_at=created), updated_at=created + timedelta(hours=1))
        )

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is not None
        assert (found.created_at, found.updated_at) == (BASE, BASE + timedelta(hours=1))


@all_stores
def test_saving_an_item_again_replaces_its_fields(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(title="Old title"))
        store.save_item(an_item(title="New title"))

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is not None
        assert found.title == "New title"


@all_stores
def test_saving_an_item_again_keeps_a_single_row(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(title="Old title"))
        store.save_item(an_item(title="New title"))

        # Execute
        listed = store.list_items()

        # Assert
        assert titles(listed) == ["New title"]


@all_stores
def test_deleting_an_item_removes_it(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item())

        # Execute
        store.delete_item("i1")

        # Assert
        assert store.get_item("i1") is None


@all_stores
def test_deleting_an_unknown_item_leaves_other_items_untouched(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        item = an_item()
        store.save_item(item)

        # Execute
        store.delete_item("missing")

        # Assert
        assert store.get_item(item.id) == item


@all_stores
def test_saving_an_item_for_an_unknown_capture_raises_unknown_capture_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(UnknownCaptureError):
        # Execute / Assert
        store.save_item(an_item(capture_id="missing"))


@all_stores
def test_saving_an_item_for_an_unknown_capture_stores_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with pytest.raises(UnknownCaptureError):
            store.save_item(an_item(capture_id="missing"))

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is None


@all_stores
def test_list_items_returns_every_item_when_unfiltered(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="One", created_at=minutes_after(1)))
        store.save_item(an_item(id="i2", title="Two", created_at=minutes_after(2)))

        # Execute
        listed = store.list_items()

        # Assert
        assert titles(listed) == ["Two", "One"]


@all_stores
def test_list_items_filters_by_stage(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Wanted", stage=Stage.WANT_TO))
        store.save_item(an_item(id="i2", title="Inbox", stage=Stage.INBOX))

        # Execute
        listed = store.list_items(stage=Stage.WANT_TO)

        # Assert
        assert titles(listed) == ["Wanted"]


@all_stores
def test_list_items_filters_by_item_type(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="A book", item_type=ItemType.BOOK))
        store.save_item(an_item(id="i2", title="A place", item_type=ItemType.PLACE))

        # Execute
        listed = store.list_items(item_type=ItemType.BOOK)

        # Assert
        assert titles(listed) == ["A book"]


@all_stores
def test_list_items_combines_stage_and_type_filters_with_and(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Match", stage=Stage.DOING, item_type=ItemType.BOOK))
        store.save_item(
            an_item(id="i2", title="Wrong stage", stage=Stage.INBOX, item_type=ItemType.BOOK)
        )
        store.save_item(
            an_item(id="i3", title="Wrong type", stage=Stage.DOING, item_type=ItemType.PLACE)
        )

        # Execute
        listed = store.list_items(stage=Stage.DOING, item_type=ItemType.BOOK)

        # Assert
        assert titles(listed) == ["Match"]


@all_stores
def test_list_items_returns_the_newest_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i2", title="Middle", created_at=minutes_after(5)))
        store.save_item(an_item(id="i1", title="Oldest", created_at=minutes_after(1)))
        store.save_item(an_item(id="i3", title="Newest", created_at=minutes_after(9)))

        # Execute
        listed = store.list_items()

        # Assert
        assert titles(listed) == ["Newest", "Middle", "Oldest"]


@all_stores
def test_list_items_created_at_the_same_instant_come_in_descending_id_order(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="a", title="Id a"))
        store.save_item(an_item(id="b", title="Id b"))

        # Execute
        listed = store.list_items()

        # Assert
        assert titles(listed) == ["Id b", "Id a"]


@all_stores
def test_list_items_orders_by_instant_rather_than_local_wall_clock(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="UTC noon", created_at=BASE))
        store.save_item(
            an_item(id="i2", title="Plus five", created_at=EARLIER_INSTANT_LATER_WALL_CLOCK)
        )

        # Execute
        listed = store.list_items()

        # Assert
        assert titles(listed) == ["UTC noon", "Plus five"]


@all_stores
def test_list_items_limit_caps_the_number_returned(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        seed_three_items(store)

        # Execute
        listed = store.list_items(limit=2)

        # Assert
        assert titles(listed) == ["Item 2", "Item 1"]


@all_stores
def test_list_items_offset_skips_the_newest(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        seed_three_items(store)

        # Execute
        listed = store.list_items(limit=1, offset=1)

        # Assert
        assert titles(listed) == ["Item 1"]


@all_stores
def test_list_items_returns_twenty_by_default(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        for minute in range(21):
            store.save_item(an_item(id=f"i{minute:02}", created_at=minutes_after(minute)))

        # Execute
        listed = store.list_items()

        # Assert
        assert len(listed) == 20


@all_stores
@pytest.mark.parametrize(("limit", "offset"), [(-1, 0), (20, -1)], ids=["limit", "offset"])
def test_list_items_with_a_negative_limit_or_offset_raises_value_error(
    open_store: StoreFactory, limit: int, offset: int
) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError):
        # Execute / Assert
        store.list_items(limit=limit, offset=offset)


@all_stores
def test_an_item_with_a_cool_off_date_reads_it_back(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(cool_off_until=date(2026, 12, 1)))

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is not None and found.cool_off_until == date(2026, 12, 1)


@all_stores
def test_an_item_without_a_cool_off_date_reads_it_back_as_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(cool_off_until=None))

        # Execute
        found = store.get_item("i1")

        # Assert
        assert found is not None and found.cool_off_until is None
