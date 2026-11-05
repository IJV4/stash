from collections.abc import Callable
from typing import Any

import pytest
from builders import (
    BARE_STRING_REFUSAL,
    BARE_STRING_TAKEAWAYS,
    BASE,
    LATER,
    fetched_outcome,
    stored_completion,
)
from fakes.memory_store import MemoryStore
from fakes.vanishing_item_store import VanishingItemStore
from lifecycle_rig import a_lifecycle

from stash.domain import Outcome
from stash.lifecycle import Lifecycle, LifecycleRefused, UnknownItem, UnknownOutcome

OUTCOME_ID = "o-i1"
NON_ITERABLE_TAKEAWAYS: Any = 5

REFUSED_EDITS: dict[str, Callable[[Lifecycle], Outcome]] = {
    "oversized-notes": lambda lifecycle: lifecycle.annotate(OUTCOME_ID, "n" * 4001, ()),
    "bare-string-takeaways": lambda lifecycle: lifecycle.annotate(
        OUTCOME_ID, "", BARE_STRING_TAKEAWAYS
    ),
    "rating-zero": lambda lifecycle: lifecycle.rate(OUTCOME_ID, 0),
}


def store_with_an_outcome() -> MemoryStore:
    store = MemoryStore()
    stored_completion(store, "i1")
    return store


def test_annotating_replaces_the_notes_and_takeaways_and_stores_the_outcome() -> None:
    # Setup
    store = store_with_an_outcome()

    # Execute
    edited = a_lifecycle(store, clock=lambda: LATER).annotate(OUTCOME_ID, "Better", ["Rest dough"])

    # Assert
    assert (edited.notes, edited.takeaways, fetched_outcome(store, OUTCOME_ID)) == (
        "Better",
        ("Rest dough",),
        edited,
    )


def test_annotating_stamps_edited_at_and_keeps_recorded_at() -> None:
    # Setup
    store = store_with_an_outcome()

    # Execute
    edited = a_lifecycle(store, clock=lambda: LATER).annotate(OUTCOME_ID, "Better", ())

    # Assert
    assert (edited.edited_at, edited.recorded_at) == (LATER, BASE)


def test_annotating_keeps_the_rating() -> None:
    # Setup
    store = store_with_an_outcome()
    rating = fetched_outcome(store, OUTCOME_ID).rating

    # Execute
    edited = a_lifecycle(store).annotate(OUTCOME_ID, "Better", ())

    # Assert
    assert edited.rating == rating


def test_rating_replaces_the_rating_and_stores_the_outcome() -> None:
    # Setup
    store = store_with_an_outcome()

    # Execute
    edited = a_lifecycle(store, clock=lambda: LATER).rate(OUTCOME_ID, 5)

    # Assert
    assert (edited.rating, fetched_outcome(store, OUTCOME_ID)) == (5, edited)


def test_rating_stamps_edited_at_and_keeps_recorded_at() -> None:
    # Setup
    store = store_with_an_outcome()

    # Execute
    edited = a_lifecycle(store, clock=lambda: LATER).rate(OUTCOME_ID, 5)

    # Assert
    assert (edited.edited_at, edited.recorded_at) == (LATER, BASE)


def test_rating_keeps_the_notes_and_takeaways() -> None:
    # Setup
    store = store_with_an_outcome()
    before = fetched_outcome(store, OUTCOME_ID)

    # Execute
    edited = a_lifecycle(store).rate(OUTCOME_ID, 5)

    # Assert
    assert (edited.notes, edited.takeaways) == (before.notes, before.takeaways)


@pytest.mark.parametrize("edit", REFUSED_EDITS.values(), ids=REFUSED_EDITS.keys())
def test_an_edit_the_domain_refuses_raises_lifecycle_refused(
    edit: Callable[[Lifecycle], Outcome],
) -> None:
    # Setup
    lifecycle = a_lifecycle(store_with_an_outcome())

    # Execute
    with pytest.raises(LifecycleRefused):
        edit(lifecycle)


@pytest.mark.parametrize("edit", REFUSED_EDITS.values(), ids=REFUSED_EDITS.keys())
def test_a_refused_edit_leaves_the_stored_outcome_unchanged(
    edit: Callable[[Lifecycle], Outcome],
) -> None:
    # Setup
    store = store_with_an_outcome()
    before = fetched_outcome(store, OUTCOME_ID)

    # Execute
    with pytest.raises(LifecycleRefused):
        edit(a_lifecycle(store))

    # Assert
    assert fetched_outcome(store, OUTCOME_ID) == before


def test_annotating_with_bare_string_takeaways_tells_the_owner_to_give_separate_items() -> None:
    # Setup
    lifecycle = a_lifecycle(store_with_an_outcome())

    # Execute
    with pytest.raises(LifecycleRefused, match=BARE_STRING_REFUSAL):
        lifecycle.annotate(OUTCOME_ID, "", BARE_STRING_TAKEAWAYS)


def test_a_wiring_bug_in_annotated_takeaways_is_not_dressed_up_as_a_refusal() -> None:
    # Setup
    lifecycle = a_lifecycle(store_with_an_outcome())

    # Execute
    with pytest.raises(TypeError):
        lifecycle.annotate(OUTCOME_ID, "", NON_ITERABLE_TAKEAWAYS)


def test_annotating_an_unknown_outcome_raises_unknown_outcome_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownOutcome) as raised:
        a_lifecycle(MemoryStore()).annotate("nope", "", ())

    # Assert
    assert raised.value.outcome_id == "nope"


def test_rating_an_unknown_outcome_raises_unknown_outcome_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownOutcome) as raised:
        a_lifecycle(MemoryStore()).rate("nope", 3)

    # Assert
    assert raised.value.outcome_id == "nope"


def test_annotating_an_outcome_whose_item_was_deleted_meanwhile_raises_unknown_item() -> None:
    # Setup
    store = VanishingItemStore()
    stored_completion(store, "i1")
    store.vanish_item_after_reading_outcome(OUTCOME_ID)

    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(store).annotate(OUTCOME_ID, "Better", ())

    # Assert
    assert raised.value.item_id == "i1"


def test_rating_an_outcome_whose_item_was_deleted_meanwhile_raises_unknown_item() -> None:
    # Setup
    store = VanishingItemStore()
    stored_completion(store, "i1")
    store.vanish_item_after_reading_outcome(OUTCOME_ID)

    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(store).rate(OUTCOME_ID, 3)

    # Assert
    assert raised.value.item_id == "i1"


def test_annotating_without_takeaways_keeps_the_current_takeaways() -> None:
    # Setup
    store = store_with_an_outcome()
    before = fetched_outcome(store, OUTCOME_ID)

    # Execute
    edited = a_lifecycle(store).annotate(OUTCOME_ID, "Better")

    # Assert
    assert (edited.notes, edited.takeaways, fetched_outcome(store, OUTCOME_ID)) == (
        "Better",
        before.takeaways,
        edited,
    )


def test_annotating_with_none_as_takeaways_keeps_the_current_takeaways() -> None:
    # Setup
    store = store_with_an_outcome()
    before = fetched_outcome(store, OUTCOME_ID)

    # Execute
    edited = a_lifecycle(store).annotate(OUTCOME_ID, "Better", None)

    # Assert
    assert edited.takeaways == before.takeaways


def test_annotating_with_an_empty_list_clears_the_takeaways() -> None:
    # Setup
    store = store_with_an_outcome()

    # Execute
    edited = a_lifecycle(store).annotate(OUTCOME_ID, "Better", [])

    # Assert
    assert edited.takeaways == ()
