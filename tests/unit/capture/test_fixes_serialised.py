from builders import BASE
from capture_builders import store_with_filed_item
from fakes.memory_store import MemoryStore
from fakes.overlap_waiting_lifecycle import OverlapWaitingLifecycle
from lifecycle_rig import a_lifecycle
from threads import run_concurrently

from stash.capture import FixHandler, Reply, Reroute

OVERLAP_GRACE_SECONDS = 0.01
SIMULTANEOUS_PRESSES = 2
FILED_ITEM_ID = "c1"
DONE_PRESS = f"stash:d:{FILED_ITEM_ID}"


def handler_whose_history_reads_overlap(store: MemoryStore) -> FixHandler:
    lifecycle = OverlapWaitingLifecycle(a_lifecycle(store), OVERLAP_GRACE_SECONDS)
    return FixHandler(store, lifecycle, lambda: BASE)


def pressed_simultaneously(handler: FixHandler) -> list[Reply | Reroute]:
    answers: list[Reply | Reroute] = []
    errors = run_concurrently(
        SIMULTANEOUS_PRESSES, lambda _: answers.append(handler.apply(DONE_PRESS))
    )
    assert errors == []
    return answers


def test_two_simultaneous_done_presses_on_a_not_yet_done_item_record_exactly_one_outcome() -> None:
    # Setup
    store, _ = store_with_filed_item()
    handler = handler_whose_history_reads_overlap(store)

    # Execute
    pressed_simultaneously(handler)

    # Assert
    assert len(store.outcomes_for(FILED_ITEM_ID)) == 1


def test_two_simultaneous_done_presses_on_a_not_yet_done_item_get_the_same_reply() -> None:
    # Setup
    store, _ = store_with_filed_item()
    handler = handler_whose_history_reads_overlap(store)

    # Execute
    first, second = pressed_simultaneously(handler)

    # Assert
    assert first == second
