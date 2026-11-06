import logging

from fakes.fake_planning_actions import FakePlanningActions
from fakes.memory_store import MemoryStore
from log_records import recording_logs
from planning_builders import DATE_NIGHT_ID, stored_date_night
from step_builders import a_step

from stash.capture import gone
from stash.capture.callback_log import CallbackLog
from stash.capture.planning_buttons import PlanningButtons
from stash.capture.planning_replies import step_done_reply, steps_saved_reply, steps_skipped_reply
from stash.capture.replies import refused
from stash.planning.errors import PlanningRefused, UnknownItem, UnknownStep

LOGGER_NAME = "stash.capture.test_planning_buttons"
A_STEP = a_step(item_id=DATE_NIGHT_ID)


def buttons_over(store: MemoryStore, planning: FakePlanningActions) -> PlanningButtons:
    return PlanningButtons(store, planning, CallbackLog(logging.getLogger(LOGGER_NAME)))


def a_store_with_a_date_night() -> MemoryStore:
    store = MemoryStore()
    stored_date_night(store)
    return store


def test_accepting_answers_that_the_prep_was_saved_with_the_confirmed_steps() -> None:
    # Setup
    store = a_store_with_a_date_night()
    buttons = buttons_over(store, FakePlanningActions((A_STEP,)))

    # Execute
    reply = buttons.accept(DATE_NIGHT_ID)

    # Assert
    assert reply == steps_saved_reply(store.list_items()[0], (A_STEP,))


def test_skipping_answers_that_the_proposed_steps_were_dropped() -> None:
    # Setup
    store = a_store_with_a_date_night()
    buttons = buttons_over(store, FakePlanningActions())

    # Execute
    reply = buttons.skip(DATE_NIGHT_ID)

    # Assert
    assert reply == steps_skipped_reply(store.list_items()[0])


def test_completing_a_step_answers_which_step_is_done() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions((A_STEP,)))

    # Execute
    reply = buttons.step_done(A_STEP.id)

    # Assert
    assert reply == step_done_reply(A_STEP)


def test_accepting_for_an_item_the_planning_does_not_know_answers_gone() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownItem("ghost")))

    # Execute
    reply = buttons.accept("ghost")

    # Assert
    assert reply == gone()


def test_accepting_for_an_item_the_planning_does_not_know_is_logged_as_an_unknown_item() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownItem("ghost")))

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.accept("ghost")

    # Assert
    assert recorder.entries() == [(logging.INFO, "fix callback for unknown item ghost")]


def test_skipping_for_an_item_the_planning_does_not_know_is_logged_as_an_unknown_item() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownItem("ghost")))

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.skip("ghost")

    # Assert
    assert recorder.entries() == [(logging.INFO, "fix callback for unknown item ghost")]


def test_completing_a_step_the_planning_does_not_know_answers_gone() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownStep("ghost")))

    # Execute
    reply = buttons.step_done("ghost")

    # Assert
    assert reply == gone()


def test_completing_a_step_the_planning_does_not_know_is_logged_as_an_unknown_step() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownStep("ghost")))

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.step_done("ghost")

    # Assert
    assert recorder.entries() == [(logging.INFO, "fix callback for unknown step ghost")]


def test_completing_a_step_whose_item_vanished_is_logged_as_an_unknown_item() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=UnknownItem("ghost")))

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.step_done("s1")

    # Assert
    assert recorder.entries() == [(logging.INFO, "fix callback for unknown item ghost")]


def test_accepting_what_the_planning_refuses_answers_the_refusal() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=PlanningRefused("not now")))

    # Execute
    reply = buttons.accept(DATE_NIGHT_ID)

    # Assert
    assert reply == refused("not now")


def test_skipping_what_the_planning_refuses_answers_the_refusal() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=PlanningRefused("not now")))

    # Execute
    reply = buttons.skip(DATE_NIGHT_ID)

    # Assert
    assert reply == refused("not now")


def test_completing_what_the_planning_refuses_answers_the_refusal() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions(error=PlanningRefused("not now")))

    # Execute
    reply = buttons.step_done("s1")

    # Assert
    assert reply == refused("not now")


def test_accepting_for_an_item_gone_by_the_time_its_title_is_read_answers_gone() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions((A_STEP,)))

    # Execute
    reply = buttons.accept(DATE_NIGHT_ID)

    # Assert
    assert reply == gone()


def test_accepting_for_an_item_gone_by_the_time_its_title_is_read_is_logged_as_unknown() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions((A_STEP,)))

    # Execute
    with recording_logs(LOGGER_NAME) as recorder:
        buttons.accept(DATE_NIGHT_ID)

    # Assert
    assert recorder.entries() == [(logging.INFO, f"fix callback for unknown item {DATE_NIGHT_ID}")]


def test_skipping_for_an_item_gone_by_the_time_its_title_is_read_answers_gone() -> None:
    # Setup
    buttons = buttons_over(MemoryStore(), FakePlanningActions())

    # Execute
    reply = buttons.skip(DATE_NIGHT_ID)

    # Assert
    assert reply == gone()
