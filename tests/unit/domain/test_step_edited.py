from datetime import date

import pytest
from step_builders import a_step

from stash.domain.step import EXACTLY_ONE_DUE, NOTHING_TO_EDIT

NEW_DAY = date(2027, 2, 1)


def test_editing_the_text_changes_only_the_text() -> None:
    # Setup
    step = a_step(text="Book the table", lead_days=7)

    # Execute
    edited = step.edited(text="Call the venue")

    # Assert
    assert (edited.text, edited.lead_days, edited.due_on) == ("Call the venue", 7, None)


def test_editing_the_lead_days_clears_the_absolute_date() -> None:
    # Setup
    step = a_step(lead_days=None, due_on=NEW_DAY)

    # Execute
    edited = step.edited(lead_days=3)

    # Assert
    assert (edited.lead_days, edited.due_on) == (3, None)


def test_editing_the_absolute_date_clears_the_lead_days() -> None:
    # Setup
    step = a_step(lead_days=7, due_on=None)

    # Execute
    edited = step.edited(due_on=NEW_DAY)

    # Assert
    assert (edited.lead_days, edited.due_on) == (None, NEW_DAY)


def test_editing_the_lead_days_to_zero_is_an_edit_and_not_nothing() -> None:
    # Setup
    step = a_step(lead_days=7)

    # Execute
    edited = step.edited(lead_days=0)

    # Assert
    assert edited.lead_days == 0


def test_editing_the_text_and_the_due_date_together_changes_both() -> None:
    # Setup
    step = a_step(lead_days=7)

    # Execute
    edited = step.edited(text="Pay the deposit", due_on=NEW_DAY)

    # Assert
    assert (edited.text, edited.lead_days, edited.due_on) == ("Pay the deposit", None, NEW_DAY)


def test_an_edit_keeps_the_identity_position_confirmation_and_progress() -> None:
    # Setup
    step = a_step(id="s9", item_id="i9", position=4, confirmed=True, done=True)

    # Execute
    edited = step.edited(text="Call the venue")

    # Assert
    assert (edited.id, edited.item_id, edited.position, edited.confirmed, edited.done) == (
        "s9",
        "i9",
        4,
        True,
        True,
    )


def test_editing_both_lead_days_and_the_absolute_date_is_refused() -> None:
    # Setup
    step = a_step()

    # Execute / Assert
    with pytest.raises(ValueError, match=EXACTLY_ONE_DUE):
        step.edited(lead_days=3, due_on=NEW_DAY)


def test_editing_nothing_is_refused() -> None:
    # Setup
    step = a_step()

    # Execute / Assert
    with pytest.raises(ValueError, match=NOTHING_TO_EDIT):
        step.edited()


def test_editing_the_text_to_blank_is_refused() -> None:
    # Setup
    step = a_step()

    # Execute / Assert
    with pytest.raises(ValueError, match="text"):
        step.edited(text="   ")


def test_editing_the_lead_days_above_the_maximum_is_refused() -> None:
    # Setup
    step = a_step()

    # Execute / Assert
    with pytest.raises(ValueError, match="lead_days"):
        step.edited(lead_days=61)
