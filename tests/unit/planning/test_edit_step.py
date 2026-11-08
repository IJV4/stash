import pytest
from fakes.store_factories import FreshStore
from step_edit_rig import NEW_DAY, date_night_with, existing

from stash.domain import STEP_TEXT_LIMIT
from stash.planning import PlanningRefused, UnknownStep


def test_editing_the_lead_time_of_a_dated_step_clears_its_date() -> None:
    # Setup
    planning = date_night_with(FreshStore(), existing(lead_days=None, due_on=NEW_DAY))

    # Execute
    edited = planning.edit_step("s1", lead_days=3)

    # Assert
    assert (edited.lead_days, edited.due_on) == (3, None)


def test_editing_the_date_of_a_step_clears_its_lead_time() -> None:
    # Setup
    planning = date_night_with(FreshStore(), existing(lead_days=7))

    # Execute
    edited = planning.edit_step("s1", due_on=NEW_DAY)

    # Assert
    assert (edited.lead_days, edited.due_on) == (None, NEW_DAY)


def test_editing_the_text_to_more_than_the_limit_is_refused() -> None:
    # Setup
    planning = date_night_with(FreshStore(), existing())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1", text="x" * (STEP_TEXT_LIMIT + 1))


def test_editing_both_a_lead_time_and_a_date_is_refused() -> None:
    # Setup
    planning = date_night_with(FreshStore(), existing())

    # Execute / Assert
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1", lead_days=2, due_on=NEW_DAY)


def test_a_refused_edit_leaves_the_stored_step_alone() -> None:
    # Setup
    store = FreshStore()
    planning = date_night_with(store, existing())

    # Execute
    with pytest.raises(PlanningRefused):
        planning.edit_step("s1", lead_days=99)

    # Assert
    assert store.get_step("s1") == existing()


def test_completing_an_unknown_step_is_refused() -> None:
    # Setup
    planning = date_night_with(FreshStore())

    # Execute / Assert
    with pytest.raises(UnknownStep):
        planning.complete_step("nope")
