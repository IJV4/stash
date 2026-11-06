from datetime import date

import pytest
from builders import MAX_LENGTH_ID
from capture_builders import button_labels
from planning_builders import DATE_NIGHT_ID, DATE_NIGHT_ON, a_date_night
from step_builders import a_step

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT
from stash.capture.planning_replies import (
    proposal_reply,
    step_done_reply,
    steps_saved_reply,
    steps_skipped_reply,
)
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, Reply
from stash.domain import Step
from stash.planning.results import Proposal

FRIDAY_FEB_5 = date(2027, 2, 5)
FRIDAY_MAR_5 = date(2027, 3, 5)
STEP_TEXT_AT_THE_LIMIT = "x" * 200
TEN_STEPS = 10


def proposed(*steps: Step, **item_overrides: object) -> Proposal:
    return Proposal(a_date_night(**item_overrides), steps)


def a_proposed_step(**overrides: object) -> Step:
    return a_step(item_id=DATE_NIGHT_ID, **overrides)


def when_text_of(step: Step) -> str:
    reply = proposal_reply(proposed(step), DATE_NIGHT_ON)
    return reply.text.splitlines()[1].rsplit(" — ", 1)[1]


def test_a_proposal_reply_is_headed_by_the_title_and_the_weekday_and_date_of_the_item() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step()), DATE_NIGHT_ON)

    # Assert
    assert reply.text.splitlines()[0] == "🗓 Prep for Date night (Fri Feb 12):"


def test_a_proposal_reply_does_not_zero_pad_the_day_of_the_item_date() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step()), FRIDAY_MAR_5)

    # Assert
    assert reply.text.splitlines()[0] == "🗓 Prep for Date night (Fri Mar 5):"


def test_a_proposal_reply_lists_each_step_as_a_bullet_with_when_it_is_due() -> None:
    # Setup
    book = a_proposed_step(id="s1", text="Book the table", lead_days=7)
    flowers = a_proposed_step(id="s2", text="Order flowers", lead_days=1, position=1)

    # Execute
    reply = proposal_reply(proposed(book, flowers), DATE_NIGHT_ON)

    # Assert
    assert reply.text.splitlines()[1:3] == [
        "• Book the table — 7 days before",
        "• Order flowers — 1 day before",
    ]


def test_a_proposal_reply_ends_by_inviting_changes() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step()), DATE_NIGHT_ON)

    # Assert
    assert reply.text.splitlines()[-1] == "Tell me changes any time."


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


def test_a_proposal_reply_offers_looks_good_and_no_steps_in_one_row() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step()), DATE_NIGHT_ON)

    # Assert
    assert button_labels(reply.buttons) == [["Looks good ✓", "No steps"]]


def test_the_buttons_of_a_proposal_reply_carry_the_item_id() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step()), DATE_NIGHT_ON)

    # Assert
    assert [[button.data for button in row] for row in reply.buttons] == [
        [f"stash:a:{DATE_NIGHT_ID}", f"stash:n:{DATE_NIGHT_ID}"]
    ]


def test_the_buttons_of_a_proposal_reply_for_the_longest_item_id_fit_the_callback_limit() -> None:
    # Execute
    reply = proposal_reply(proposed(a_proposed_step(), id=MAX_LENGTH_ID), DATE_NIGHT_ON)

    # Assert
    assert max(len(b.data.encode("utf-8")) for row in reply.buttons for b in row) <= (
        TELEGRAM_CALLBACK_LIMIT
    )


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


def test_saving_three_steps_says_how_many_were_saved_and_that_reminders_will_follow() -> None:
    # Setup
    steps = tuple(a_proposed_step(id=f"s{n}", position=n) for n in range(3))

    # Execute
    reply = steps_saved_reply(a_date_night(), steps)

    # Assert
    assert reply.text == "✅ Prep saved for Date night: 3 steps. I'll remind you when each is due."


def test_saving_one_step_says_one_step_in_the_singular() -> None:
    # Execute
    reply = steps_saved_reply(a_date_night(), (a_proposed_step(),))

    # Assert
    assert reply.text == "✅ Prep saved for Date night: 1 step. I'll remind you when each is due."


def test_saving_no_steps_says_there_are_no_proposed_steps_any_more() -> None:
    # Execute
    reply = steps_saved_reply(a_date_night(), ())

    # Assert
    assert reply.text == "There are no proposed steps for Date night any more."


def test_skipping_the_steps_says_the_proposed_steps_were_dropped() -> None:
    # Execute
    reply = steps_skipped_reply(a_date_night())

    # Assert
    assert reply.text == "Okay, I dropped the proposed steps for Date night."


def test_completing_a_step_says_which_step_is_done() -> None:
    # Execute
    reply = step_done_reply(a_proposed_step(text="Book the table"))

    # Assert
    assert reply.text == "✅ Done: Book the table"


def test_a_proposal_without_steps_says_there_is_nothing_to_prep_and_offers_no_buttons() -> None:
    # Execute
    reply = proposal_reply(proposed(), DATE_NIGHT_ON)

    # Assert
    assert reply == Reply("🗓 Nothing to prep for Date night (Fri Feb 12).")
