from datetime import date

import pytest
from planning_builders import DATE_NIGHT_ID, DATE_NIGHT_ON, a_date_night
from step_builders import a_step

from stash.capture.planning_replies import (
    proposal_reply,
    step_done_reply,
    steps_saved_reply,
)
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.domain import Step
from stash.planning.results import Proposal

FRIDAY_FEB_5 = date(2027, 2, 5)
STEP_TEXT_AT_THE_LIMIT = "x" * 200
TEN_STEPS = 10


def proposed(*steps: Step, **item_overrides: object) -> Proposal:
    return Proposal(a_date_night(**item_overrides), steps)


def a_proposed_step(**overrides: object) -> Step:
    return a_step(item_id=DATE_NIGHT_ID, **overrides)


def when_text_of(step: Step) -> str:
    reply = proposal_reply(proposed(step), DATE_NIGHT_ON)
    return reply.text.splitlines()[1].rsplit(" — ", 1)[1]


@pytest.mark.parametrize(
    ("overrides", "when"),
    [
        ({"lead_days": 0}, "same day"),
        ({"lead_days": 1}, "1 day before"),
        ({"lead_days": 5}, "5 days before"),
        ({"lead_days": 60}, "60 days before"),
        ({"lead_days": None, "due_on": FRIDAY_FEB_5}, "Fri Feb 5"),
    ],
)
def test_a_step_says_when_it_is_due_in_the_words_of_its_lead_time_or_its_date(
    overrides: dict[str, object], when: str
) -> None:
    # Execute / Assert
    assert when_text_of(a_proposed_step(**overrides)) == when


def test_a_proposal_of_ten_steps_at_the_text_limit_fits_a_telegram_message() -> None:
    # Setup
    steps = tuple(
        a_proposed_step(id=f"s{n}", text=STEP_TEXT_AT_THE_LIMIT, lead_days=n, position=n)
        for n in range(TEN_STEPS)
    )

    # Execute
    reply = proposal_reply(proposed(*steps), DATE_NIGHT_ON)

    # Assert
    assert len(reply.text) <= TELEGRAM_TEXT_LIMIT


def test_saving_no_steps_says_there_are_no_proposed_steps_any_more() -> None:
    # Execute
    reply = steps_saved_reply(a_date_night(), ())

    # Assert
    assert reply.text == "There are no proposed steps for Date night any more."


def test_completing_a_step_says_which_step_is_done() -> None:
    # Execute
    reply = step_done_reply(a_proposed_step(text="Book the table"))

    # Assert
    assert reply.text == "✅ Done: Book the table"
