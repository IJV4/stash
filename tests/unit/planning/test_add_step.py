import pytest
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from fakes.watched_step_store import WatchedStepStore
from planning_rig import planning_over
from step_edit_rig import DATE_NIGHT_ID, date_night_with

from stash.domain import STEP_TEXT_LIMIT
from stash.planning import PlanningRefused, UnknownItem


def test_adding_a_step_to_an_unknown_item_is_refused() -> None:
    # Setup
    planning = planning_over(FreshStore(), FakeStepProposals())

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
    planning = date_night_with(FreshStore())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "  ", lead_days=10)


def test_adding_a_step_with_text_over_the_limit_is_refused() -> None:
    # Setup
    planning = date_night_with(FreshStore())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.add_step(DATE_NIGHT_ID, "x" * (STEP_TEXT_LIMIT + 1), lead_days=10)


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
