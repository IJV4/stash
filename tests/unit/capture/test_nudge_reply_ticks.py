from nudge_builders import SATURDAY_MORNING, stored_long_step_reminders
from nudge_rig import a_nudge_rig

from stash.capture.replies import TELEGRAM_TEXT_LIMIT

STEP_REMINDERS_TO_DELIVER = 60
TICKS_ENOUGH_FOR_ALL = 20
REMINDERS_PER_MESSAGE = 13


def test_sixty_long_step_reminders_are_all_delivered_over_successive_ticks() -> None:
    # Setup
    rig = a_nudge_rig()
    stored_long_step_reminders(rig.store, STEP_REMINDERS_TO_DELIVER)
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    rig.tick_through([SATURDAY_MORNING] * TICKS_ENOUGH_FOR_ALL)

    # Assert
    delivered = sorted(line[2:4] for _, text in rig.sent_texts() for line in text.splitlines())
    assert delivered == [f"{number:02d}" for number in range(STEP_REMINDERS_TO_DELIVER)]


def test_a_tick_marks_sent_only_the_reminders_it_showed() -> None:
    # Setup
    rig = a_nudge_rig()
    stored_long_step_reminders(rig.store, STEP_REMINDERS_TO_DELIVER)
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    rig.tick(SATURDAY_MORNING)

    # Assert
    still_due = len(rig.nudger.due(SATURDAY_MORNING))
    assert still_due == STEP_REMINDERS_TO_DELIVER - REMINDERS_PER_MESSAGE


def test_every_message_the_sixty_reminders_make_fits_the_telegram_limit() -> None:
    # Setup
    rig = a_nudge_rig()
    stored_long_step_reminders(rig.store, STEP_REMINDERS_TO_DELIVER)
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    rig.tick_through([SATURDAY_MORNING] * TICKS_ENOUGH_FOR_ALL)

    # Assert
    assert max(len(text) for _, text in rig.sent_texts()) <= TELEGRAM_TEXT_LIMIT
