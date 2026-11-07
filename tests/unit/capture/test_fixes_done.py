from datetime import date

from builders import BASE, LATER, PLANNED_FOR, an_item, fetched_item, stored
from capture_builders import (
    COMPLETED_ITEM_ID,
    COMPLETED_TITLE,
    a_store_with_a_completed_item,
    store_with_filed_item,
    text_of,
)
from capture_rig import a_fix_handler
from fakes.memory_store import MemoryStore

from stash.capture import gone
from stash.capture.completion_replies import done_reply
from stash.domain import Stage
from stash.lifecycle.results import Completion

YESTERDAY = date(2026, 11, 1)


def test_pressing_done_answers_the_done_reply_for_the_new_outcome() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:d:c1")

    # Assert
    [outcome] = store.outcomes_for("c1")
    assert reply == done_reply(Completion(fetched_item(store, "c1"), outcome, repeat=False))


def test_pressing_done_moves_the_item_to_done() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    a_fix_handler(store).apply("stash:d:c1")

    # Assert
    assert fetched_item(store, "c1").stage is Stage.DONE


def test_pressing_done_on_a_done_item_long_after_its_outcome_answers_the_repeat_reply() -> None:
    # Setup
    store = a_store_with_a_completed_item()

    # Execute
    reply = a_fix_handler(store, lambda: LATER).apply(f"stash:d:{COMPLETED_ITEM_ID}")

    # Assert
    assert text_of(reply).splitlines()[0] == f"🎉 Done: {COMPLETED_TITLE} (again)"


def test_pressing_done_for_an_unknown_item_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:d:ghost")

    # Assert
    assert reply == gone()


def test_pressing_done_on_an_item_dated_before_today_completes_it_on_its_date() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(stage=Stage.PLANNED, date=YESTERDAY))

    # Execute
    a_fix_handler(store).apply("stash:d:i1")

    # Assert
    [outcome] = store.outcomes_for("i1")
    assert outcome.completed_on == YESTERDAY


def test_pressing_done_on_an_item_dated_after_today_completes_it_today() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(stage=Stage.PLANNED, date=PLANNED_FOR))

    # Execute
    a_fix_handler(store).apply("stash:d:i1")

    # Assert
    [outcome] = store.outcomes_for("i1")
    assert outcome.completed_on == BASE.date()
