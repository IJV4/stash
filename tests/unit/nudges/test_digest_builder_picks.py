import pytest
from builders import stored
from digest_builders import (
    DIGEST_AT,
    SAIL_REASON,
    a_digest_builder,
    a_due_digest,
    a_forgotten_sail,
    building,
)
from fakes.fake_pick_source import FakePickSource
from fakes.memory_store import MemoryStore
from nudge_builders import a_stuck_book

from stash.domain import Pick
from stash.nudges.digest_builder import DIGEST_CONTEXT


def test_the_digest_asks_for_three_picks_for_the_coming_week() -> None:
    # Setup
    source = FakePickSource()

    # Execute
    a_digest_builder(MemoryStore(), source).build(a_due_digest(), DIGEST_AT)

    # Assert
    assert source.asked == [(DIGEST_CONTEXT, 3)]


def test_the_picks_context_asks_for_things_worth_doing_in_the_coming_week() -> None:
    # Assert
    assert DIGEST_CONTEXT == "Pick things worth doing in the coming week."


def test_the_digest_carries_the_picks_it_was_given() -> None:
    # Setup
    pick = Pick(a_forgotten_sail(), SAIL_REASON)
    builder = a_digest_builder(MemoryStore(), FakePickSource([pick]))

    # Execute
    built = builder.build(a_due_digest(), DIGEST_AT)

    # Assert
    assert built.sections.picks == (pick,)


def test_a_digest_without_picks_has_an_empty_picks_section() -> None:
    # Execute
    sections = building(MemoryStore())

    # Assert
    assert sections.picks == ()


def test_the_built_digest_keeps_its_instant_and_its_stuck_items() -> None:
    # Setup
    due = a_due_digest(DIGEST_AT, a_stuck_book())
    builder = a_digest_builder(MemoryStore())

    # Execute
    built = builder.build(due, DIGEST_AT)

    # Assert
    assert (built.due_at, built.stuck) == (due.due_at, due.stuck)


def test_building_records_nothing_as_sent() -> None:
    # Setup
    store = MemoryStore()
    stored(store, a_forgotten_sail())
    built = a_digest_builder(store).build(a_due_digest(), DIGEST_AT)

    # Execute
    recorded = [store.was_sent(nudge.key) for nudge in built.nudges]

    # Assert
    assert recorded == [False, False]


def test_building_with_a_now_that_has_no_time_zone_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="now"):
        a_digest_builder(MemoryStore()).build(a_due_digest(), DIGEST_AT.replace(tzinfo=None))
