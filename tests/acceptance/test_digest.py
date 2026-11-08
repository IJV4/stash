from datetime import timedelta

import pytest
from builders import stored
from digest_builders import (
    DIGEST_AT,
    SAIL_ID,
    SAIL_REASON,
    a_forgotten_sail,
    a_forgotten_want_to,
    stored_every_section,
)
from digest_rig import a_digest_rig
from fakes.failing_nudge_sender import FailingNudgeSender
from fakes.ledger_recording_store import LedgerRecordingStore
from fakes.store_factories import FreshStore
from nudge_builders import (
    LONG_AGO,
    SATURDAY,
    SUNDAY_NOON,
    a_planned_date_night,
    a_stuck_book,
)
from nudge_rig import MINUTE
from suggestion_builders import a_raw_pick, picks_reply

from stash.capture.digest_replies import DIGEST_HEADER
from stash.domain import NudgeKind
from stash.llm import LlmDeferred, LlmUnavailable

SIX_DIGESTS_SPAN = timedelta(weeks=5, days=1)
NO_SUGGESTIONS = picks_reply()
DIGESTS_WITHOUT_THE_SUGGESTIONS_SECTION = "\n".join(
    [
        "🗞 Your weekly digest",
        "🆕 New this week",
        "• Pasta carbonara",
        "• Ramen",
        "🕰 Forgotten",
        "• Learn to sail",
        "📅 Coming up",
        "• Fri Feb 12 — Book the table (Date night)",
        "• Sat Feb 13 — Date night",
        "📖 How is Thinking in Systems going?",
    ]
)
FORGOTTEN_AND_STUCK_TEXT = "\n".join(
    [
        "🗞 Your weekly digest",
        "🕰 Forgotten",
        "• Learn to sail",
        "📖 How is Thinking in Systems going?",
    ]
)
REMINDERS_FILLING_THE_MESSAGE = 13
WEEKLY_DIGEST_TEXT = "\n".join(
    [
        DIGESTS_WITHOUT_THE_SUGGESTIONS_SECTION,
        "💡 Ideas for this week",
        f"• Learn to sail — {SAIL_REASON}",
    ]
)


def test_a_digest_with_every_section_lists_new_forgotten_coming_up_stuck_and_suggestions() -> None:
    # Setup
    store = FreshStore()
    stored_every_section(store)
    rig = a_digest_rig(store, [picks_reply(a_raw_pick(SAIL_ID, SAIL_REASON))])

    # Execute
    rig.tick(DIGEST_AT)

    # Assert
    assert rig.sent_texts() == [(DIGEST_AT, WEEKLY_DIGEST_TEXT)]


@pytest.mark.parametrize("outage", [LlmUnavailable("down"), LlmDeferred("gpu busy")], ids=repr)
def test_with_the_model_unavailable_the_digest_goes_out_at_once_without_its_suggestions(
    outage: LlmUnavailable,
) -> None:
    # Setup
    store = FreshStore()
    stored_every_section(store)
    rig = a_digest_rig(store, [outage])

    # Execute
    rig.tick(DIGEST_AT)

    # Assert
    assert rig.sent_texts() == [(DIGEST_AT, DIGESTS_WITHOUT_THE_SUGGESTIONS_SECTION)]


def test_a_forgotten_item_is_absent_from_the_next_four_digests_and_may_return_in_the_fifth() -> (
    None
):
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_sail())
    rig = a_digest_rig(store, [NO_SUGGESTIONS] * 6)
    six_digests = rig.schedule.digest_instants_between(DIGEST_AT, DIGEST_AT + SIX_DIGESTS_SPAN)

    # Execute
    for instant in six_digests:
        rig.tick(instant)

    # Assert
    assert [("Learn to sail" in text) for _, text in rig.sent_texts()] == [
        True,
        False,
        False,
        False,
        False,
        True,
    ]


def test_the_forgotten_section_shows_the_three_oldest_items_oldest_first() -> None:
    # Setup
    store = FreshStore()
    for age, title in enumerate(["Fifth", "Fourth", "Third", "Second", "First"]):
        updated = LONG_AGO + timedelta(days=age)
        stored(store, a_forgotten_want_to(title.lower(), title=title, updated_at=updated))
    rig = a_digest_rig(store, [NO_SUGGESTIONS])

    # Execute
    rig.tick(DIGEST_AT)

    # Assert
    assert rig.sent_texts() == [
        (DIGEST_AT, f"{DIGEST_HEADER}\n🕰 Forgotten\n• Fifth\n• Fourth\n• Third")
    ]


def test_a_failed_send_records_nothing_so_the_retry_sends_the_whole_digest() -> None:
    # Setup
    store = FreshStore()
    stored(store, a_forgotten_sail())
    stored(store, a_stuck_book())
    rig = a_digest_rig(store, [NO_SUGGESTIONS] * 2, send=FailingNudgeSender(failures=1))
    rig.tick(DIGEST_AT)

    # Execute
    rig.tick(DIGEST_AT + MINUTE)

    # Assert
    assert rig.sent_texts() == [(DIGEST_AT + MINUTE, FORGOTTEN_AND_STUCK_TEXT)]


def test_a_crash_while_recording_the_digest_repeats_the_whole_digest() -> None:
    # Setup
    store = LedgerRecordingStore()
    stored(store, a_forgotten_sail())
    stored(store, a_stuck_book())
    rig = a_digest_rig(store, [NO_SUGGESTIONS] * 2)
    store.crash_on = NudgeKind.DIGEST
    rig.tick(DIGEST_AT)
    store.crash_on = None

    # Execute
    rig.tick(DIGEST_AT + MINUTE)

    # Assert
    assert rig.sent_texts() == [
        (DIGEST_AT, FORGOTTEN_AND_STUCK_TEXT),
        (DIGEST_AT + MINUTE, FORGOTTEN_AND_STUCK_TEXT),
    ]


def test_a_digest_that_does_not_fit_beside_the_reminders_leaves_only_the_reminders_sent() -> None:
    # Setup
    store = LedgerRecordingStore()
    for number in range(REMINDERS_FILLING_THE_MESSAGE):
        stored(store, a_planned_date_night(id=f"night{number}", title="T" * 400, date=SATURDAY))
    stored(store, a_forgotten_want_to(SAIL_ID, title="x" * 400, updated_at=LONG_AGO))
    stored(store, a_stuck_book())
    rig = a_digest_rig(store, [NO_SUGGESTIONS] * 2)

    # Execute
    rig.tick(SUNDAY_NOON)

    # Assert
    assert store.recorded == [NudgeKind.ITEM_DATE] * REMINDERS_FILLING_THE_MESSAGE
