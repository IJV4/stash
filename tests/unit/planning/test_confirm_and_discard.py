import pytest
from builders import stored_item
from fakes.fake_step_proposals import FakeStepProposals
from fakes.memory_store import MemoryStore
from fakes.watched_step_store import WatchedStepStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_builders import a_step
from step_edit_rig import confirmed, date_night_with, proposed

from stash.planning import UnknownItem


def test_confirming_all_confirms_every_proposed_step() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0), proposed("s2", 1))

    # Execute
    planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert [step.confirmed for step in store.steps_for(DATE_NIGHT_ID)] == [True, True]


def test_confirming_all_returns_the_confirmed_steps_in_order() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), proposed("s1", 0), proposed("s2", 1))

    # Execute
    steps = planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert [(step.id, step.confirmed) for step in steps] == [("s1", True), ("s2", True)]


def test_confirmed_steps_become_open_steps_that_can_remind() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0))

    # Execute
    planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert [step.id for step in store.open_confirmed_steps()] == ["s1"]


def test_confirming_twice_returns_the_same_steps() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), proposed("s1", 0))
    first = planning.confirm_all(DATE_NIGHT_ID)

    # Execute
    second = planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert second == first


def test_confirming_an_item_without_steps_returns_nothing_and_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals())

    # Execute
    steps = planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert (steps, store.step_writes) == ((), 0)


def test_confirming_leaves_another_items_steps_alone() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0))
    stored_item(store, id="other", title="Other")
    store.save_steps("other", [a_step(id="s9", item_id="other", confirmed=False)])

    # Execute
    planning.confirm_all(DATE_NIGHT_ID)

    # Assert
    assert [step.confirmed for step in store.steps_for("other")] == [False]


def test_confirming_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(MemoryStore(), FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.confirm_all("nope")


def test_confirming_for_an_item_deleted_just_before_the_write_is_unknown() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, [proposed("s1", 0)])
    store.vanish_before_next_step_write(DATE_NIGHT_ID)
    planning = planning_over(store, FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.confirm_all(DATE_NIGHT_ID)


def test_discarding_removes_the_proposed_steps() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0), proposed("s2", 1))

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == []


def test_discarding_keeps_the_steps_already_confirmed() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, confirmed("s1", 0), proposed("s2", 1))

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert [step.id for step in store.steps_for(DATE_NIGHT_ID)] == ["s1"]


def test_discarding_after_confirming_changes_nothing() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0))
    confirmed_steps = planning.confirm_all(DATE_NIGHT_ID)

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert store.steps_for(DATE_NIGHT_ID) == list(confirmed_steps)


def test_discarding_leaves_another_items_proposed_steps_alone() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, proposed("s1", 0))
    stored_item(store, id="other", title="Other")
    store.save_steps("other", [a_step(id="s9", item_id="other", confirmed=False)])

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert [step.id for step in store.steps_for("other")] == ["s9"]


def test_discarding_for_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(MemoryStore(), FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.discard("nope")


def test_discarding_for_an_item_deleted_just_before_the_write_is_unknown() -> None:
    # Setup
    store = WatchedStepStore()
    stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, [proposed("s1", 0)])
    store.vanish_before_next_step_write(DATE_NIGHT_ID)
    planning = planning_over(store, FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.discard(DATE_NIGHT_ID)
