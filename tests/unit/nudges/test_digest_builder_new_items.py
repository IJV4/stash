from datetime import timedelta

from builders import MICROSECOND, an_item, stored
from digest_builders import (
    DIGEST_AT,
    ONE_DAY,
    a_digest_builder,
    a_due_digest,
    a_new_want_to,
    building,
)
from fakes.memory_store import MemoryStore

from stash.domain import Stage


def new_item_ids(store: MemoryStore) -> list[str]:
    return [item.id for item in building(store).new_items]


def test_new_items_are_those_created_in_the_week_before_the_digest_newest_first() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_new_want_to("older", 5))
    stored(store, a_new_want_to("newest", 1))
    stored(store, a_new_want_to("middle", 3))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == ["newest", "middle", "older"]


def test_an_item_created_exactly_a_week_before_the_digest_is_new() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_new_want_to("on-the-edge", 7))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == ["on-the-edge"]


def test_an_item_created_a_microsecond_before_the_week_began_is_not_new() -> None:
    # Setup
    store = MemoryStore()
    created = DIGEST_AT - timedelta(days=7) - MICROSECOND
    stored(store, an_item(id="just-missed", created_at=created, updated_at=created))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == []


def test_an_item_created_a_microsecond_before_the_digest_instant_is_new() -> None:
    # Setup
    store = MemoryStore()
    created = DIGEST_AT - MICROSECOND
    stored(store, an_item(id="just-in-time", created_at=created, updated_at=created))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == ["just-in-time"]


def test_an_item_created_at_the_digest_instant_is_not_new() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(id="too-late", created_at=DIGEST_AT, updated_at=DIGEST_AT))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == []


def test_a_dropped_item_is_not_new() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_new_want_to("dropped", 2, stage=Stage.DROPPED))
    stored(store, a_new_want_to("kept", 2))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert ids == ["kept"]


def test_new_items_of_every_other_stage_are_listed() -> None:
    # Setup
    store = MemoryStore()
    for stage in (Stage.INBOX, Stage.WANT_TO, Stage.DOING, Stage.DONE):
        stored(store, a_new_want_to(f"in-{stage.value}", 2, stage=stage))

    # Execute
    ids = new_item_ids(store)

    # Assert
    assert len(ids) == 4


def test_the_week_is_counted_back_from_the_digest_instant_not_from_the_moment_of_building() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_new_want_to("before-the-digest", 1))
    stored(store, a_new_want_to("after-the-digest", -1))
    builder = a_digest_builder(store)

    # Execute
    built = builder.build(a_due_digest(), DIGEST_AT + 3 * ONE_DAY)

    # Assert
    assert [item.id for item in built.sections.new_items] == ["before-the-digest"]
