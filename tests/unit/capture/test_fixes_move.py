from builders import fetched_item
from capture_builders import store_with_filed_item
from capture_rig import a_fix_handler
from fakes.busy_store import BusyStore
from fakes.faulty_store import FaultyStore

from stash.capture import gone
from stash.capture.replies import busy, confirmation
from stash.domain import Stage
from stash.store import UnknownItemError


def test_pressing_a_stage_moves_the_item_and_confirms_it() -> None:
    # Setup
    store, _ = store_with_filed_item()

    # Execute
    reply = a_fix_handler(store).apply("stash:S:c1:doing")

    # Assert
    moved = fetched_item(store, "c1")
    assert (moved.stage, reply) == (Stage.DOING, confirmation(moved, unsure=False))


def test_pressing_a_stage_while_the_store_is_busy_answers_busy() -> None:
    # Setup
    store, _ = store_with_filed_item(BusyStore())

    # Execute
    reply = a_fix_handler(store).apply("stash:S:c1:doing")

    # Assert
    assert reply == busy()


def test_pressing_a_stage_for_an_item_another_process_deleted_answers_gone() -> None:
    # Setup
    store, _ = store_with_filed_item(FaultyStore(fail_on={"update_item": UnknownItemError("c1")}))

    # Execute
    reply = a_fix_handler(store).apply("stash:S:c1:doing")

    # Assert
    assert reply == gone()
