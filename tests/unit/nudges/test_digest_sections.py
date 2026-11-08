from datetime import date, timedelta

import pytest
from digest_builders import SAIL_REASON, a_forgotten_want_to
from nudge_builders import (
    SATURDAY,
    a_planned_date_night,
    a_same_day_step,
    a_stuck_book,
)
from people_builders import a_key_date, a_person
from planning_builders import DATE_NIGHT_ID

from stash.domain import Pick
from stash.nudges.digest import (
    FORGOTTEN_LIMIT,
    NEW_WINDOW,
    PICK_LIMIT,
    UPCOMING_DAYS,
    DigestSections,
    UpcomingItem,
    UpcomingPersonDate,
    UpcomingStep,
)


def test_the_digest_names_its_limits_and_windows() -> None:
    # Assert
    assert (
        3,
        3,
        timedelta(days=7),
        14,
    ) == (FORGOTTEN_LIMIT, PICK_LIMIT, NEW_WINDOW, UPCOMING_DAYS)


def test_an_upcoming_item_on_another_date_than_the_item_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="not the date of"):
        UpcomingItem(date(2027, 2, 20), a_planned_date_night())


def test_an_upcoming_step_on_another_date_than_the_step_is_due_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="not the due date of"):
        UpcomingStep(SATURDAY, a_planned_date_night(), a_same_day_step(lead_days=1))


def test_an_upcoming_step_for_a_step_of_another_item_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="belongs to item"):
        UpcomingStep(SATURDAY, a_stuck_book(), a_same_day_step(item_id=DATE_NIGHT_ID))


def test_an_upcoming_person_date_for_a_key_date_of_another_person_is_refused() -> None:
    # Setup
    strangers_key_date = a_key_date(person_id="someone-else")

    # Execute / Assert
    with pytest.raises(ValueError, match="belongs to"):
        UpcomingPersonDate(SATURDAY, a_person(), strangers_key_date)


def test_sections_with_more_forgotten_items_than_the_limit_are_refused() -> None:
    # Setup
    forgotten = tuple(a_forgotten_want_to(f"f{n}") for n in range(FORGOTTEN_LIMIT + 1))

    # Execute / Assert
    with pytest.raises(ValueError, match="forgotten"):
        DigestSections((), forgotten, (), ())


def test_sections_with_more_picks_than_the_limit_are_refused() -> None:
    # Setup
    picks = tuple(Pick(a_forgotten_want_to(f"p{n}"), SAIL_REASON) for n in range(PICK_LIMIT + 1))

    # Execute / Assert
    with pytest.raises(ValueError, match="picks"):
        DigestSections((), (), (), picks)
