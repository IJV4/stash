import logging

import pytest
from capture_rig import a_fix_handler, logged_by_applying
from fakes.chat_model import FakeChatModel
from fakes.memory_store import MemoryStore
from planning_builders import DATE_NIGHT_ID, steps_reply, stored_date_night
from planning_rig import a_planning

from stash.capture import gone
from stash.capture.fixes import FixHandler
from stash.capture.planning_replies import step_done_reply, steps_saved_reply, steps_skipped_reply
from stash.domain import Item, Step
from stash.planning import Planning

PROPOSED_STEP_COUNT = 3
LOOKS_GOOD = f"stash:a:{DATE_NIGHT_ID}"
NO_STEPS = f"stash:n:{DATE_NIGHT_ID}"


class ProposedPrep:
    def __init__(self) -> None:
        self.store = MemoryStore()
        self.item: Item = stored_date_night(self.store)
        planning: Planning = a_planning(self.store, FakeChatModel(steps_reply(PROPOSED_STEP_COUNT)))
        self.steps: tuple[Step, ...] = planning.propose_for(DATE_NIGHT_ID).steps
        self.fixes: FixHandler = a_fix_handler(self.store, planning=planning)

    @property
    def confirmed(self) -> tuple[Step, ...]:
        return tuple(step.confirmed_now() for step in self.steps)


def test_looks_good_answers_that_the_prep_was_saved_with_the_number_of_steps() -> None:
    # Setup
    prep = ProposedPrep()

    # Execute
    reply = prep.fixes.apply(LOOKS_GOOD)

    # Assert
    assert reply == steps_saved_reply(prep.item, prep.confirmed)


def test_pressing_looks_good_twice_answers_the_same_prep_saved_reply() -> None:
    # Setup
    prep = ProposedPrep()
    first = prep.fixes.apply(LOOKS_GOOD)

    # Execute
    second = prep.fixes.apply(LOOKS_GOOD)

    # Assert
    assert second == first


def test_pressing_looks_good_twice_leaves_the_steps_confirmed_exactly_once() -> None:
    # Setup
    prep = ProposedPrep()
    prep.fixes.apply(LOOKS_GOOD)

    # Execute
    prep.fixes.apply(LOOKS_GOOD)

    # Assert
    assert prep.store.steps_for(DATE_NIGHT_ID) == list(prep.confirmed)


def test_no_steps_answers_that_the_proposed_steps_were_dropped() -> None:
    # Setup
    prep = ProposedPrep()

    # Execute
    reply = prep.fixes.apply(NO_STEPS)

    # Assert
    assert reply == steps_skipped_reply(prep.item)


def test_looks_good_after_no_steps_answers_that_there_are_no_proposed_steps_any_more() -> None:
    # Setup
    prep = ProposedPrep()
    prep.fixes.apply(NO_STEPS)

    # Execute
    reply = prep.fixes.apply(LOOKS_GOOD)

    # Assert
    assert reply == steps_saved_reply(prep.item, ())


def test_looks_good_after_no_steps_confirms_nothing() -> None:
    # Setup
    prep = ProposedPrep()
    prep.fixes.apply(NO_STEPS)

    # Execute
    prep.fixes.apply(LOOKS_GOOD)

    # Assert
    assert prep.store.steps_for(DATE_NIGHT_ID) == []


def test_no_steps_after_looks_good_keeps_the_confirmed_steps() -> None:
    # Setup
    prep = ProposedPrep()
    prep.fixes.apply(LOOKS_GOOD)

    # Execute
    prep.fixes.apply(NO_STEPS)

    # Assert
    assert prep.store.steps_for(DATE_NIGHT_ID) == list(prep.confirmed)


def test_pressing_a_step_done_answers_which_step_is_done() -> None:
    # Setup
    prep = ProposedPrep()
    step = prep.confirmed[0]

    # Execute
    reply = prep.fixes.apply(f"stash:x:{step.id}")

    # Assert
    assert reply == step_done_reply(step)


def test_pressing_a_step_done_marks_that_step_done() -> None:
    # Setup
    prep = ProposedPrep()
    step = prep.steps[0]

    # Execute
    prep.fixes.apply(f"stash:x:{step.id}")

    # Assert
    assert prep.store.get_step(step.id) == step.confirmed_now().marked_done()


def test_pressing_a_step_done_leaves_the_other_steps_open() -> None:
    # Setup
    prep = ProposedPrep()

    # Execute
    prep.fixes.apply(f"stash:x:{prep.steps[0].id}")

    # Assert
    assert prep.store.steps_for(DATE_NIGHT_ID)[1:] == list(prep.steps[1:])


@pytest.mark.parametrize("data", ["stash:a:ghost", "stash:n:ghost"])
def test_pressing_a_prep_button_for_an_unknown_item_answers_gone(data: str) -> None:
    # Setup
    handler = a_fix_handler(MemoryStore())

    # Execute / Assert
    assert handler.apply(data) == gone()


@pytest.mark.parametrize("data", ["stash:a:ghost", "stash:n:ghost"])
def test_pressing_a_prep_button_for_an_unknown_item_is_logged_at_info(data: str) -> None:
    # Execute / Assert
    assert logged_by_applying(MemoryStore(), data) == [
        (logging.INFO, "fix callback for unknown item ghost")
    ]


def test_pressing_a_step_done_for_an_unknown_step_answers_gone() -> None:
    # Setup
    handler = a_fix_handler(MemoryStore())

    # Execute / Assert
    assert handler.apply("stash:x:ghost") == gone()


def test_pressing_a_step_done_for_an_unknown_step_is_logged_at_info() -> None:
    # Execute / Assert
    assert logged_by_applying(MemoryStore(), "stash:x:ghost") == [
        (logging.INFO, "fix callback for unknown step ghost")
    ]


@pytest.mark.parametrize(
    "data", ["stash:a:", "stash:n:", "stash:x:", "stash:a:i1:1", "stash:x:s1:1"]
)
def test_forged_prep_button_data_answers_gone(data: str) -> None:
    # Setup
    handler = a_fix_handler(MemoryStore())

    # Execute / Assert
    assert handler.apply(data) == gone()


@pytest.mark.parametrize("data", ["stash:a:", "stash:x:s1:1"])
def test_forged_prep_button_data_is_logged_as_unparseable(data: str) -> None:
    # Execute / Assert
    assert logged_by_applying(MemoryStore(), data) == [
        (logging.WARNING, f"unparseable fix callback: {data!r}")
    ]
