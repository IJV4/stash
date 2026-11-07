from datetime import date

from builders import in_los_angeles
from capture_builders import a_filing_answer, a_message
from capture_narrowing import handle_filed
from capture_rig import build_rig
from fakes.memory_store import MemoryStore
from nudge_builders import DIGEST_LINE
from nudge_rig import a_nudge_rig
from people_builders import a_directory, stored_ana_with_a_march_sixth_birthday

from stash.domain import KeyDateKind

MARCH_SIXTH = date(2027, 3, 6)
FEBRUARY_TWENTIETH_MORNING = in_los_angeles(date(2027, 2, 20), 9)
MARCH_FOURTH_MORNING = in_los_angeles(date(2027, 3, 4), 9)
MARCH_SIXTH_MORNING = in_los_angeles(MARCH_SIXTH, 9)
FEBRUARY_TWENTY_FIRST_MORNING = in_los_angeles(date(2027, 2, 21), 9)
MARCH_FIFTH_MORNING = in_los_angeles(date(2027, 3, 5), 9)
MARCH_SEVENTH_MORNING = in_los_angeles(date(2027, 3, 7), 9)
MARCH_SIXTH_NOON = in_los_angeles(MARCH_SIXTH, 12)
TWO_DAYS_BEFORE_LINE = "🎂 Ana's birthday in 2 days (Sat Mar 6)."
NO_GIFT_IDEAS_LINE = "No gift ideas saved yet."
ON_THE_DAY_LINE = "🎂 Today: Ana's birthday (turns 34)."


def test_a_birthday_is_reminded_fourteen_days_before_two_days_before_and_on_the_day() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)
    rig = a_nudge_rig(store)
    ticks = [FEBRUARY_TWENTIETH_MORNING, MARCH_FOURTH_MORNING, MARCH_SIXTH_MORNING]
    for tick in ticks:
        rig.digests_before_were_sent(tick)

    # Execute
    rig.tick_through(ticks)

    # Assert
    assert rig.sent_texts() == [
        (
            FEBRUARY_TWENTIETH_MORNING,
            f"🎂 Ana's birthday in 14 days (Sat Mar 6).\n{NO_GIFT_IDEAS_LINE}",
        ),
        (MARCH_FOURTH_MORNING, f"{TWO_DAYS_BEFORE_LINE}\n{NO_GIFT_IDEAS_LINE}"),
        (MARCH_SIXTH_MORNING, ON_THE_DAY_LINE),
    ]


def test_birthday_reminders_missed_with_the_pc_off_arrive_with_the_digest_in_one_message() -> None:
    # Setup
    store = MemoryStore()
    stored_ana_with_a_march_sixth_birthday(store)
    rig = a_nudge_rig(store)
    pc_goes_off = in_los_angeles(date(2027, 2, 20), 8)
    rig.digests_before_were_sent(pc_goes_off)
    rig.tick(pc_goes_off)

    # Execute
    rig.tick_through([MARCH_SIXTH_NOON])

    # Assert
    assert rig.sent_texts() == [
        (
            MARCH_SIXTH_NOON,
            "\n".join(
                [
                    "While I was offline:",
                    ON_THE_DAY_LINE,
                    DIGEST_LINE,
                ]
            ),
        )
    ]


def test_a_gift_idea_filed_before_the_person_was_added_appears_in_their_reminder() -> None:
    # Setup
    capture = build_rig(
        answer=a_filing_answer(item_type="gift", title="ceramic class", details={}, people=["Ana"])
    )
    handle_filed(capture, a_message("gift idea for Ana: ceramic class"))
    ana = capture.people.add("Ana")
    capture.people.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6, 1993)
    rig = a_nudge_rig(capture.store)
    rig.digests_before_were_sent(FEBRUARY_TWENTIETH_MORNING)

    # Execute
    rig.tick_through([FEBRUARY_TWENTIETH_MORNING])

    # Assert
    assert rig.sent_texts() == [
        (
            FEBRUARY_TWENTIETH_MORNING,
            "🎂 Ana's birthday in 14 days (Sat Mar 6).\nGift ideas: • ceramic class",
        )
    ]


def test_a_birthday_added_twice_is_reminded_only_for_the_corrected_date() -> None:
    # Setup
    store = MemoryStore()
    directory = a_directory(store)
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6, 1993)
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 7, 1993)
    rig = a_nudge_rig(store)
    ticks = [FEBRUARY_TWENTY_FIRST_MORNING, MARCH_FIFTH_MORNING, MARCH_SEVENTH_MORNING]
    for tick in ticks:
        rig.digests_before_were_sent(tick)

    # Execute
    rig.tick_through(ticks)

    # Assert
    assert [text for _, text in rig.sent_texts()] == [
        f"🎂 Ana's birthday in 14 days (Sun Mar 7).\n{NO_GIFT_IDEAS_LINE}",
        f"🎂 Ana's birthday in 2 days (Sun Mar 7).\n{NO_GIFT_IDEAS_LINE}",
        "🎂 Today: Ana's birthday (turns 34).",
    ]
