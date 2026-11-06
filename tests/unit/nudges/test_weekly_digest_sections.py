from digest_builders import DIGEST_AT, a_forgotten_sail, a_forgotten_want_to
from nudge_builders import STUCK_BOOK_ID, a_stuck_book

from stash.domain import Nudge, NudgeKey, NudgeKind, utc_text
from stash.nudges import StuckItem, WeeklyDigest
from stash.nudges.digest import EMPTY_SECTIONS, DigestSections
from stash.nudges.due import DIGEST_SUBJECT


def a_digest_with_forgotten(*forgotten: str) -> WeeklyDigest:
    items = tuple(a_forgotten_want_to(item_id) for item_id in forgotten)
    return WeeklyDigest(DIGEST_AT, (), DigestSections((), items, (), ()))


def test_a_digest_nobody_filled_in_has_empty_sections() -> None:
    # Execute
    digest = WeeklyDigest(DIGEST_AT, ())

    # Assert
    assert digest.sections == EMPTY_SECTIONS


def test_a_forgotten_item_is_recorded_as_a_forgotten_nudge_at_the_digest_instant() -> None:
    # Setup
    digest = WeeklyDigest(DIGEST_AT, (), DigestSections((), (a_forgotten_sail(),), (), ()))

    # Execute
    nudges = digest.nudges

    # Assert
    assert nudges[0] == Nudge(NudgeKind.FORGOTTEN, "sail", DIGEST_AT, "Learn to sail")


def test_the_ledger_key_of_a_forgotten_item_is_forgotten_the_item_id_and_the_digest_instant() -> (
    None
):
    # Setup
    digest = WeeklyDigest(DIGEST_AT, (), DigestSections((), (a_forgotten_sail(),), (), ()))

    # Execute
    key = digest.nudges[0].key

    # Assert
    assert key == NudgeKey("forgotten", "sail", utc_text(DIGEST_AT))


def test_a_digest_is_recorded_as_its_stuck_items_then_its_forgotten_items_then_itself() -> None:
    # Setup
    stuck = (StuckItem(a_stuck_book(), DIGEST_AT),)
    forgotten = (a_forgotten_want_to("f1"), a_forgotten_want_to("f2"))
    digest = WeeklyDigest(DIGEST_AT, stuck, DigestSections((), forgotten, (), ()))

    # Execute
    recorded = [(nudge.kind, nudge.subject_id) for nudge in digest.nudges]

    # Assert
    assert recorded == [
        (NudgeKind.STUCK, STUCK_BOOK_ID),
        (NudgeKind.FORGOTTEN, "f1"),
        (NudgeKind.FORGOTTEN, "f2"),
        (NudgeKind.DIGEST, DIGEST_SUBJECT),
    ]


def test_a_digest_with_nothing_forgotten_is_recorded_as_before() -> None:
    # Setup
    digest = a_digest_with_forgotten()

    # Execute
    recorded = [nudge.kind for nudge in digest.nudges]

    # Assert
    assert recorded == [NudgeKind.DIGEST]
