from datetime import date

import pytest
from digest_builders import a_digest_with
from nudge_builders import a_nudge_message
from people_builders import a_key_date, a_person, a_person_date_reminder

from stash.capture.digest_replies import render_digest
from stash.capture.nudge_replies import nudge_reply
from stash.capture.wording import LINE_LIMIT
from stash.domain import KeyDateKind
from stash.nudges import UpcomingPersonDate
from stash.nudges.due import PersonDateReminder


def text_of(reminder: PersonDateReminder) -> str:
    return nudge_reply(a_nudge_message(reminder)).reply.text


def test_the_gift_ideas_line_is_clipped_like_every_other_line() -> None:
    # Execute
    text = text_of(a_person_date_reminder(lead=2, gift_ideas=("x" * 400,)))

    # Assert
    assert len(text.splitlines()[1]) == LINE_LIMIT


@pytest.mark.parametrize(
    "year", [pytest.param(None, id="no-year"), pytest.param(2027, id="born-this-year"), 2030]
)
def test_a_birthday_on_the_day_never_shows_an_age_that_is_missing_zero_or_negative(
    year: int | None,
) -> None:
    # Setup
    ana = a_person(name="Ana", aliases=())
    key_date = a_key_date(person_id=ana.id, month=3, day=6, year=year)

    # Execute
    text = text_of(a_person_date_reminder(person=ana, key_date=key_date))

    # Assert
    assert text == "🎂 Today: Ana's birthday."


@pytest.mark.parametrize(
    ("kind", "label", "expected"),
    [
        (KeyDateKind.ANNIVERSARY, "Wedding", "💍 Today: Ana's anniversary."),
        (KeyDateKind.OTHER, "Graduation", "📅 Today: Ana's Graduation."),
        (KeyDateKind.OTHER, "", "📅 Today: Ana's key date."),
    ],
)
def test_the_emoji_and_the_occasion_follow_the_kind_of_key_date(
    kind: KeyDateKind, label: str, expected: str
) -> None:
    # Setup
    ana = a_person(name="Ana", aliases=())
    key_date = a_key_date(person_id=ana.id, kind=kind, label=label, month=3, day=6)

    # Execute
    text = text_of(a_person_date_reminder(person=ana, key_date=key_date))

    # Assert
    assert text == expected


def test_a_coming_up_key_date_is_listed_with_its_day_emoji_and_occasion() -> None:
    # Setup
    ana = a_person(name="Ana", aliases=())
    entry = UpcomingPersonDate(date(2027, 3, 6), ana, a_key_date(person_id=ana.id, month=3, day=6))

    # Execute
    reply = render_digest(a_digest_with(upcoming=[entry]))

    # Assert
    assert "• Sat Mar 6 — 🎂 Ana's birthday" in reply.text.splitlines()
