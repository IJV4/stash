import pytest
from fakes.memory_store import MemoryStore
from step_edit_rig import DATE_NIGHT_ID, NEW_DAY, date_night_with, existing

from stash.planning import PlanningRefused, UnknownStep


def test_editing_the_text_stores_and_returns_the_changed_step() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing())

    # Execute
    edited = planning.edit_step("s1", text="Call the venue")

    # Assert
    assert (edited.text, store.get_step("s1")) == ("Call the venue", edited)


def test_editing_the_lead_time_of_a_dated_step_clears_its_date() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing(lead_days=None, due_on=NEW_DAY))

    # Execute
    edited = planning.edit_step("s1", lead_days=3)

    # Assert
    assert (edited.lead_days, edited.due_on) == (3, None)


def test_editing_the_date_of_a_step_clears_its_lead_time() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing(lead_days=7))

    # Execute
    edited = planning.edit_step("s1", due_on=NEW_DAY)

    # Assert
    assert (edited.lead_days, edited.due_on) == (None, NEW_DAY)


def test_editing_an_unknown_step_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute / Assert
    with pytest.raises(UnknownStep) as refusal:
        planning.edit_step("nope", text="x")
    assert refusal.value.step_id == "nope"


def test_editing_nothing_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1")


def test_editing_both_a_lead_time_and_a_date_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1", lead_days=2, due_on=NEW_DAY)


def test_a_refused_edit_leaves_the_stored_step_alone() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing())

    # Execute
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1", lead_days=99)

    # Assert
    assert store.get_step("s1") == existing()


def test_completing_a_step_marks_it_done_and_stores_it() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing(confirmed=True))

    # Execute
    done = planning.complete_step("s1")

    # Assert
    assert (done.done, store.get_step("s1")) == (True, done)


def test_a_completed_step_is_no_longer_open() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing(confirmed=True))

    # Execute
    planning.complete_step("s1")

    # Assert
    assert store.open_confirmed_steps() == []


def test_completing_a_step_twice_leaves_it_done() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing(confirmed=True))
    planning.complete_step("s1")

    # Execute
    again = planning.complete_step("s1")

    # Assert
    assert again.done is True


def test_completing_an_unknown_step_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute / Assert
    with pytest.raises(UnknownStep):
        planning.complete_step("nope")


def test_completing_a_proposed_step_confirms_it() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing(confirmed=False))

    # Execute
    completed = planning.complete_step("s1")

    # Assert
    assert (completed.confirmed, completed.done) == (True, True)


def test_a_proposed_step_completed_by_the_owner_survives_a_later_no_steps_press() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store, existing(confirmed=False))
    planning.complete_step("s1")

    # Execute
    planning.discard(DATE_NIGHT_ID)

    # Assert
    assert [(step.id, step.confirmed, step.done) for step in store.steps_for(DATE_NIGHT_ID)] == [
        ("s1", True, True)
    ]
