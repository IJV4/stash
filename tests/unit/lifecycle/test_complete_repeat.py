import pytest
from builders import BASE, LATER, an_item_at, fetched_item, stored, stored_completion
from fakes.failing_completion_store import CompletionFailed, FailingCompletionStore
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage


@pytest.mark.parametrize(
    ("stored_kept", "keep", "expected_kept"),
    [(True, None, True), (False, True, True), (True, False, False)],
    ids=["unchanged-when-none", "kept-when-true", "unkept-when-false"],
)
def test_completing_a_done_item_is_a_repeat_whose_kept_follows_the_keep_argument(
    stored_kept: bool, keep: bool | None, expected_kept: bool
) -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "i1", kept=stored_kept)

    # Execute
    done = a_lifecycle(store).complete("i1", keep=keep)

    # Assert
    assert (done.item.stage, done.item.kept, done.repeat) == (Stage.DONE, expected_kept, True)


def test_a_repeat_without_keep_leaves_the_stored_item_exactly_as_it_was() -> None:
    # Setup
    store = MemoryStore()
    original = stored_completion(store, "i1", kept=True)

    # Execute
    done = a_lifecycle(store, clock=lambda: LATER).complete("i1")

    # Assert
    assert (done.item, store.get_item("i1")) == (original, original)


def test_a_repeat_adds_an_outcome_and_keeps_the_first_one_unchanged() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "i1", kept=True)
    first = store.outcomes_for("i1")[0]

    # Execute
    done = a_lifecycle(store, clock=lambda: LATER).complete("i1", rating=5)

    # Assert
    assert store.outcomes_for("i1") == [first, done.outcome]


def test_a_first_completion_is_not_a_repeat_even_when_other_items_are_done() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "other")
    stored(store, an_item_at(Stage.DOING, id="i1"))

    # Execute
    done = a_lifecycle(store).complete("i1")

    # Assert
    assert done.repeat is False


def test_retrying_a_completion_whose_write_failed_is_a_first_completion_not_a_repeat() -> None:
    # Setup
    store = FailingCompletionStore()
    stored(store, an_item_at(Stage.DOING))
    lifecycle = a_lifecycle(store)
    store.fail_next_completion = True
    with pytest.raises(CompletionFailed):
        lifecycle.complete("i1")

    # Execute
    retried = lifecycle.complete("i1")

    # Assert
    assert (retried.repeat, retried.item.stage, store.outcomes_for("i1")) == (
        False,
        Stage.DONE,
        [retried.outcome],
    )


def test_a_failed_completion_write_leaves_the_item_in_its_stage_with_no_outcome() -> None:
    # Setup
    store = FailingCompletionStore()
    stored(store, an_item_at(Stage.DOING))
    store.fail_next_completion = True

    # Execute
    with pytest.raises(CompletionFailed):
        a_lifecycle(store, clock=lambda: BASE).complete("i1")

    # Assert
    assert (fetched_item(store, "i1").stage, store.outcomes_for("i1")) == (Stage.DOING, [])
