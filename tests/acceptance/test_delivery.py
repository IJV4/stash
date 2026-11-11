import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, time, timedelta

import pytest
from builders import stored
from digest_builders import stored_every_section
from digest_rig import a_digest_rig
from fakes.chat_model import FakeChatModel
from fakes.failing_nudge_sender import FailingNudgeSender
from fakes.fake_step_proposals import FakeStepProposals
from fakes.ledger_recording_store import LedgerCrashed, LedgerRecordingStore
from fakes.scripted_sender import SendFailed
from fakes.store_factories import FreshStore
from log_records import recording_logs
from nudge_builders import (
    SATURDAY_MORNING,
    SUNDAY,
    SUNDAY_DIGEST_TIME,
    SUNDAY_MORNING,
    SUNDAY_NOON,
    a_date_reminder,
    a_nudge_schedule,
    a_person_dates,
    a_planned_date_night,
    stored_date_night_with_its_step,
)
from nudge_rig import HOUR, MINUTE, UnbuiltDigests, a_nudge_rig
from planning_builders import (
    DATE_NIGHT_ID,
    DATE_NIGHT_ON,
    RESCHEDULED_ON,
    a_date_night,
    a_raw_step,
    stored_date_night,
)
from planning_rig import a_planning, planning_over
from suggestion_builders import picks_reply

from stash.capture import Reply, proposal_reply
from stash.delivery import NudgeDelivery, ProposalDelivery
from stash.delivery.nudges import ALREADY_RECORDED_LOG, SEND_FAILED_LOG
from stash.delivery.proposals import PROPOSAL_SEND_FAILED_LOG
from stash.domain import STEP_TEXT_LIMIT, NudgeKind
from stash.llm import LlmBadOutput, LlmError, LlmUnavailable
from stash.nudges import Nudger
from stash.planning import MAX_PROPOSED_STEPS, Planning, Proposal, ProposedStep
from stash.store import StoreBusyError

NUDGE_LOGGER = "stash.delivery.nudges"
PROPOSAL_LOGGER = "stash.delivery.proposals"
DIGEST_TIME = time(10, 0)
JUST_AFTER_THE_DIGEST = SUNDAY_DIGEST_TIME + 5 * MINUTE
A_WEEK_LATER = SUNDAY_NOON + timedelta(days=7)
ALL_KINDS = {
    NudgeKind.STEP,
    NudgeKind.ITEM_DATE,
    NudgeKind.FOLLOWUP,
    NudgeKind.DIGEST,
    NudgeKind.STUCK,
    NudgeKind.FORGOTTEN,
}
LONG_REMINDERS = 20
PROPOSALS = (ProposedStep("Book the table", 7),)
SAT_WEEK_REMINDER_TEXT = (
    "⏰ Book the table — for Date night (Sat Feb 13)\n📅 Date night (Sat Feb 13)"
)


def telegram_is_down(reply: Reply) -> None:
    raise SendFailed("secret chat text")


def a_stash_after_its_first_run_with_everything_due() -> LedgerRecordingStore:
    store = LedgerRecordingStore()
    stored_every_section(store)
    return store


def test_the_first_tick_records_every_due_kind_of_nudge_without_sending_any() -> None:
    # Setup
    store = a_stash_after_its_first_run_with_everything_due()
    rig = a_digest_rig(store, [picks_reply()], first_run=True)

    # Execute
    rig.tick(SUNDAY_NOON)

    # Assert
    assert (rig.sent, set(store.recorded)) == ([], ALL_KINDS)


def test_a_message_another_sender_recorded_meanwhile_is_logged_and_not_sent_again() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)

    def another_sender_records_the_date_reminder(reply: Reply) -> None:
        store.record_all_sent([a_date_reminder().nudge], SATURDAY_MORNING)

    rig = a_nudge_rig(store, send=another_sender_records_the_date_reminder)
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    with recording_logs(NUDGE_LOGGER) as logs:
        rig.tick_through([SATURDAY_MORNING, SATURDAY_MORNING + MINUTE])

    # Assert
    assert logs.entries() == [(logging.WARNING, ALREADY_RECORDED_LOG)]


def test_a_failed_send_is_logged_by_the_error_type_only() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)

    rig = a_nudge_rig(store, send=telegram_is_down)
    rig.digests_before_were_sent(SATURDAY_MORNING)

    # Execute
    with recording_logs(NUDGE_LOGGER) as logs:
        rig.tick(SATURDAY_MORNING)

    # Assert
    assert logs.entries() == [(logging.WARNING, SEND_FAILED_LOG % "SendFailed")]


def a_stash_with_a_reminder_and_a_follow_up_due_together() -> LedgerRecordingStore:
    store = LedgerRecordingStore()
    stored(store, a_planned_date_night())
    store.record_all_sent([a_date_reminder().nudge], SATURDAY_MORNING)
    stored(store, a_planned_date_night(id="sunday-night", date=SUNDAY))
    store.crash_on = NudgeKind.ITEM_DATE
    return store


def test_a_ledger_failure_after_a_sent_message_does_not_stop_the_next_message_being_sent() -> None:
    # Setup
    store = a_stash_with_a_reminder_and_a_follow_up_due_together()
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SUNDAY_MORNING)

    # Execute
    rig.tick(SUNDAY_MORNING)

    # Assert
    assert len(rig.sent) == 2


def a_first_run_with_three_separate_messages_due() -> tuple[LedgerRecordingStore, NudgeDelivery]:
    store = LedgerRecordingStore()
    stored(store, a_planned_date_night())
    seeded = [a_date_reminder(SATURDAY_MORNING + HOUR).nudge]
    FreshStore.record_all_sent(store, seeded, SATURDAY_MORNING + HOUR)
    stored(store, a_planned_date_night(id="sunday-night", date=SUNDAY))
    schedule = a_nudge_schedule(reminder_time=DIGEST_TIME, followup_time=DIGEST_TIME)
    nudger = Nudger(store, schedule, a_person_dates(store, schedule))
    return store, NudgeDelivery(nudger, UnbuiltDigests())


def test_a_first_tick_that_cannot_record_everything_records_and_sends_nothing() -> None:
    # Setup
    store, delivery = a_first_run_with_three_separate_messages_due()
    store.crash_on = NudgeKind.DIGEST
    sent: list[Reply] = []

    # Execute
    with pytest.raises(LedgerCrashed):
        delivery.deliver(JUST_AFTER_THE_DIGEST, sent.append)

    # Assert
    assert (sent, store.recorded) == ([], [])


def test_previewing_on_the_first_run_returns_nothing_because_a_real_run_stays_silent() -> None:
    # Setup
    store = FreshStore()
    stored_date_night_with_its_step(store)
    rig = a_nudge_rig(store)

    # Execute
    replies = rig.delivery.preview(SATURDAY_MORNING)

    # Assert
    assert replies == ()


def failing_once(error: LlmError) -> Callable[[], None]:
    pending = [error]

    def fail() -> None:
        if pending:
            raise pending.pop()

    return fail


def a_planning_proposing(store: FreshStore, *, while_thinking: Callable[[], object]) -> Planning:
    return planning_over(store, FakeStepProposals(PROPOSALS, while_thinking=while_thinking))


def nothing() -> None:
    return None


def test_a_planned_dated_item_with_no_steps_is_proposed_and_the_proposal_reply_is_sent() -> None:
    # Setup
    store = FreshStore()
    item = stored_date_night(store)
    sent: list[Reply] = []

    # Execute
    ProposalDelivery(a_planning_proposing(store, while_thinking=nothing), store).deliver(
        sent.append
    )

    # Assert
    proposed = Proposal(item, tuple(store.steps_for(DATE_NIGHT_ID)))
    assert sent == [proposal_reply(proposed, DATE_NIGHT_ON)]


def test_a_proposal_the_model_leaves_empty_is_sent_as_nothing_to_prep() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    planning = planning_over(store, FakeStepProposals(()))
    sent: list[Reply] = []

    # Execute
    ProposalDelivery(planning, store).deliver(sent.append)

    # Assert
    assert sent == [Reply("🗓 Nothing to prep for Date night (Fri Feb 12).")]


def test_after_a_nothing_to_prep_message_the_item_is_not_proposed_again() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals(())
    delivery = ProposalDelivery(planning_over(store, proposals), store)
    delivery.deliver(lambda reply: None)

    # Execute
    delivery.deliver(lambda reply: None)

    # Assert
    assert len(proposals.asked_about) == 1


def test_a_model_that_answers_with_an_empty_list_gets_nothing_to_prep_sent() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    planning = a_planning(store, FakeChatModel({"steps": []}))
    sent: list[Reply] = []

    # Execute
    ProposalDelivery(planning, store).deliver(sent.append)

    # Assert
    assert sent == [Reply("🗓 Nothing to prep for Date night (Fri Feb 12).")]


@pytest.mark.parametrize(
    ("reply", "error"),
    [
        pytest.param(None, LlmBadOutput("not json"), id="unparseable"),
        pytest.param({"steps": [a_raw_step(lead_days=True)]}, None, id="every-step-invalid"),
        pytest.param({"answer": "no steps here"}, None, id="no-steps-list"),
    ],
)
def test_an_unusable_model_answer_sends_nothing_and_is_not_asked_again(
    reply: Mapping[str, object] | None, error: LlmError | None
) -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    model = FakeChatModel(reply, error)
    delivery = ProposalDelivery(a_planning(store, model), store)
    sent: list[Reply] = []

    # Execute
    with recording_logs(PROPOSAL_LOGGER) as logs:
        delivery.deliver(sent.append)
        delivery.deliver(sent.append)

    # Assert
    assert (sent, len(model.calls), logs.entries()) == ([], 1, [])


def test_at_most_three_items_are_proposed_per_call() -> None:
    # Setup
    store = FreshStore()
    for number in range(4):
        stored(store, a_date_night(id=f"night-{number}"))
    sent: list[Reply] = []

    # Execute
    ProposalDelivery(a_planning_proposing(store, while_thinking=nothing), store).deliver(
        sent.append
    )

    # Assert
    assert len(sent) == 3


def test_a_planned_item_whose_date_has_passed_is_not_proposed_and_the_model_is_not_asked() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    proposals = FakeStepProposals(PROPOSALS)
    day_after = datetime.combine(DATE_NIGHT_ON + timedelta(days=1), time(12), tzinfo=UTC)
    planning = planning_over(store, proposals, lambda: day_after)
    sent: list[Reply] = []

    # Execute
    ProposalDelivery(planning, store).deliver(sent.append)

    # Assert
    assert (sent, proposals.asked_about) == ([], [])


class PlanningThatCannotWithdraw:
    def __init__(self, planning: Planning) -> None:
        self.needs_proposal = planning.needs_proposal
        self.propose_for = planning.propose_for

    def withdraw(self, item_id: str) -> None:
        raise StoreBusyError


def two_planned_nights() -> FreshStore:
    store = FreshStore()
    stored(store, a_date_night(id="night-0"))
    stored(store, a_date_night(id="night-1"))
    return store


def test_a_withdraw_that_fails_after_a_failed_send_does_not_stop_the_next_item_being_proposed() -> (
    None
):
    # Setup
    store = two_planned_nights()
    planning = PlanningThatCannotWithdraw(a_planning_proposing(store, while_thinking=nothing))
    sent: list[Reply] = []
    first_send_fails = FailingNudgeSender(failures=1)

    def fail_the_first_send(reply: Reply) -> None:
        first_send_fails(reply)
        sent.append(reply)

    # Execute
    ProposalDelivery(planning, store).deliver(fail_the_first_send)

    # Assert
    assert len(sent) == 1


def test_a_proposal_too_long_for_one_telegram_message_is_withdrawn_and_nothing_is_sent() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    longest_steps = [
        ProposedStep("😀" * STEP_TEXT_LIMIT, lead_days)
        for lead_days in range(1, MAX_PROPOSED_STEPS + 1)
    ]
    planning = planning_over(store, FakeStepProposals(longest_steps))
    sent: list[Reply] = []

    # Execute
    with recording_logs(PROPOSAL_LOGGER) as logs:
        ProposalDelivery(planning, store).deliver(sent.append)

    # Assert
    assert (sent, store.steps_for(DATE_NIGHT_ID), logs.entries()) == (
        [],
        [],
        [(logging.WARNING, PROPOSAL_SEND_FAILED_LOG % "ValueError")],
    )


def test_a_model_outage_skips_one_item_until_the_next_call_without_stopping_the_next_item() -> None:
    # Setup
    store = two_planned_nights()
    planning = a_planning_proposing(store, while_thinking=failing_once(LlmUnavailable("down")))
    delivery = ProposalDelivery(planning, store)
    sent: list[Reply] = []

    # Execute
    delivery.deliver(sent.append)
    delivery.deliver(sent.append)

    # Assert
    assert len(sent) == 2


def test_an_item_whose_date_changed_while_the_model_thought_is_skipped_without_a_log() -> None:
    # Setup
    store = FreshStore()
    stored_date_night(store)
    moved = a_date_night(date=RESCHEDULED_ON)
    planning = a_planning_proposing(store, while_thinking=lambda: store.save_item(moved))

    # Execute
    with recording_logs(PROPOSAL_LOGGER) as logs:
        ProposalDelivery(planning, store).deliver(lambda reply: None)

    # Assert
    assert logs.entries() == []
