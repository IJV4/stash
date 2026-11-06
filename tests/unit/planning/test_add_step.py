import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.memory_store import MemoryStore
from fakes.watched_step_store import WatchedStepStore
from planning_rig import planning_over
from step_edit_rig import DATE_NIGHT_ID, LATER, NEW_DAY, date_night_with, existing

from stash.planning import PlanningRefused, UnknownItem


def test_an_added_step_is_confirmed_and_open() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store)

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)

    # Assert
    assert (step.text, step.lead_days, step.confirmed, step.done) == (
        "Buy tickets",
        10,
        True,
        False,
    )


def test_an_added_step_is_stored() -> None:
    # Setup
    store = MemoryStore()
    planning = date_night_with(store)

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)

    # Assert
    assert store.get_step(step.id) == step


def test_an_added_step_can_carry_an_absolute_date_instead_of_a_lead_time() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Pay deposit", due_on=NEW_DAY)

    # Assert
    assert (step.lead_days, step.due_on) == (None, NEW_DAY)


def test_the_first_added_step_takes_position_zero() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)

    # Assert
    assert step.position == 0


def test_an_added_step_goes_after_the_last_existing_position() -> None:
    # Setup
    planning = date_night_with(MemoryStore(), existing("s1", 0), existing("s2", 4))

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)

    # Assert
    assert step.position == 5


def test_an_added_step_is_stamped_with_the_current_instant() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute
    step = planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)

    # Assert
    assert step.created_at == LATER


def test_adding_a_step_to_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(MemoryStore(), FakeStepProposals())

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.add_step("nope", "Buy tickets", lead_days=10)


def test_adding_a_step_to_an_item_deleted_just_before_the_write_is_unknown() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store)
    store.vanish_before_next_step_write(DATE_NIGHT_ID)

    # Execute / Assert
    with pytest.raises(UnknownItem):
        planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10)


def test_adding_a_step_with_blank_text_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "  ", lead_days=10)


def test_adding_a_step_with_both_a_lead_time_and_a_date_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "Buy tickets", lead_days=10, due_on=NEW_DAY)


def test_adding_a_step_with_neither_a_lead_time_nor_a_date_is_refused() -> None:
    # Setup
    planning = date_night_with(MemoryStore())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "Buy tickets")


def test_a_refused_added_step_writes_nothing() -> None:
    # Setup
    store = WatchedStepStore()
    planning = date_night_with(store)
    writes_before = store.step_writes

    # Execute
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "  ", lead_days=10)

    # Assert
    assert store.step_writes == writes_before
