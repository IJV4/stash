import pytest
from builders import BASE
from capture_rig import a_fix_handler
from fakes.chat_model import FakeChatModel
from fakes.memory_store import MemoryStore
from fakes.scripted_chat_model import ScriptedChatModel
from planning_builders import (
    DATE_NIGHT_ID,
    DATE_NIGHT_ON,
    RESCHEDULED_ON,
    steps_reply,
    stored_date_night,
)
from planning_rig import a_planning

from stash.capture import proposal_reply
from stash.capture.planning_replies import steps_saved_reply, steps_skipped_reply
from stash.llm import LlmUnavailable


def test_a_date_night_planned_for_feb_12_gets_at_most_ten_unconfirmed_steps_and_none_is_open() -> (
    None
):
    # Setup
    store = MemoryStore()
    stored_date_night(store)
    planning = a_planning(store, FakeChatModel(steps_reply(12)))

    # Execute
    planning.propose_for(DATE_NIGHT_ID)

    # Assert
    proposed = store.steps_for(DATE_NIGHT_ID)
    assert (len(proposed), {step.confirmed for step in proposed}, store.open_confirmed_steps()) == (
        10,
        {False},
        [],
    )


def test_an_outage_proposes_nothing_and_leaves_the_item_alone_and_the_next_attempt_succeeds() -> (
    None
):
    # Setup
    store = MemoryStore()
    date_night = stored_date_night(store)
    model = ScriptedChatModel([LlmUnavailable("down"), steps_reply(3)])
    planning = a_planning(store, model)

    # Execute
    with pytest.raises(LlmUnavailable):
        planning.propose_for(DATE_NIGHT_ID)
    after_outage = (store.steps_for(DATE_NIGHT_ID), store.get_item(DATE_NIGHT_ID))
    retried = planning.propose_for(DATE_NIGHT_ID)

    # Assert
    assert (after_outage, len(retried.steps)) == (([], date_night), 3)


def test_pressing_looks_good_turns_the_proposed_steps_into_open_confirmed_steps() -> None:
    # Setup
    store = MemoryStore()
    date_night = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(steps_reply(3)))
    fixes = a_fix_handler(store, planning=planning)
    proposal = planning.propose_for(DATE_NIGHT_ID)
    [[looks_good, _]] = proposal_reply(proposal, DATE_NIGHT_ON).buttons
    confirmed = [step.confirmed_now() for step in proposal.steps]

    # Execute
    reply = fixes.apply(looks_good.data)

    # Assert
    assert store.open_confirmed_steps() == confirmed
    assert reply == steps_saved_reply(date_night, confirmed)


def test_pressing_no_steps_deletes_the_proposed_steps_and_leaves_the_item_unchanged() -> None:
    # Setup
    store = MemoryStore()
    date_night = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(steps_reply(3)))
    fixes = a_fix_handler(store, planning=planning)
    proposal = planning.propose_for(DATE_NIGHT_ID)
    [[_, no_steps]] = proposal_reply(proposal, DATE_NIGHT_ON).buttons

    # Execute
    reply = fixes.apply(no_steps.data)

    # Assert
    assert (store.steps_for(DATE_NIGHT_ID), store.get_item(DATE_NIGHT_ID)) == ([], date_night)
    assert reply == steps_skipped_reply(date_night)


def test_after_no_steps_the_item_is_not_proposed_again_until_its_date_changes() -> None:
    # Setup
    store = MemoryStore()
    date_night = stored_date_night(store)
    planning = a_planning(store, FakeChatModel(steps_reply(3)))
    fixes = a_fix_handler(store, planning=planning)
    [[_, no_steps]] = proposal_reply(planning.propose_for(DATE_NIGHT_ID), DATE_NIGHT_ON).buttons

    # Execute
    fixes.apply(no_steps.data)
    declined = planning.needs_proposal(date_night)
    moved = date_night.rescheduled(RESCHEDULED_ON, BASE)
    store.save_item(moved)
    offered_again = planning.needs_proposal(moved)

    # Assert
    assert (declined, offered_again) == (False, True)
