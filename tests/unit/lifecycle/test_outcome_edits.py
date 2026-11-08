from collections.abc import Callable
from typing import Any

import pytest
from builders import (
    BARE_STRING_REFUSAL,
    BARE_STRING_TAKEAWAYS,
    fetched_outcome,
    stored_completion,
)
from fakes.faulty_store import FaultyStore
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Outcome
from stash.lifecycle import Lifecycle, LifecycleRefused, UnknownItem, UnknownOutcome
from stash.lifecycle.service import NOTHING_TO_ANNOTATE
from stash.store import UnknownItemError

OUTCOME_ID = "o-i1"
NON_ITERABLE_TAKEAWAYS: Any = 5

REFUSED_EDITS: dict[str, Callable[[Lifecycle], Outcome]] = {
    "oversized-notes": lambda lifecycle: lifecycle.annotate(OUTCOME_ID, notes="n" * 4001),
    "bare-string-takeaways": lambda lifecycle: lifecycle.annotate(
        OUTCOME_ID, notes="", takeaways=BARE_STRING_TAKEAWAYS
    ),
    "rating-zero": lambda lifecycle: lifecycle.rate(OUTCOME_ID, 0),
    "annotated-rating-zero": lambda lifecycle: lifecycle.annotate(OUTCOME_ID, rating=0),
    "annotated-rating-six": lambda lifecycle: lifecycle.annotate(OUTCOME_ID, rating=6),
    "notes-with-a-rating-of-zero": lambda lifecycle: lifecycle.annotate(
        OUTCOME_ID, notes="Better", takeaways=["Rest dough"], rating=0
    ),
}


def store_with_an_outcome() -> FreshStore:
    store = FreshStore()
    stored_completion(store, "i1")
    return store


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
        lifecycle.annotate(OUTCOME_ID, notes="", takeaways=BARE_STRING_TAKEAWAYS)


def test_a_wiring_bug_in_annotated_takeaways_is_not_dressed_up_as_a_refusal() -> None:
    # Setup
    lifecycle = a_lifecycle(store_with_an_outcome())

    # Execute
    with pytest.raises(TypeError):
        lifecycle.annotate(OUTCOME_ID, notes="", takeaways=NON_ITERABLE_TAKEAWAYS)


def test_annotating_an_unknown_outcome_raises_unknown_outcome_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownOutcome) as raised:
        a_lifecycle(FreshStore()).annotate("nope", notes="")

    # Assert
    assert raised.value.outcome_id == "nope"


def test_rating_an_unknown_outcome_raises_unknown_outcome_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownOutcome) as raised:
        a_lifecycle(FreshStore()).rate("nope", 3)

    # Assert
    assert raised.value.outcome_id == "nope"


def test_annotating_an_outcome_whose_item_was_deleted_meanwhile_raises_unknown_item() -> None:
    # Setup
    store = FaultyStore()
    stored_completion(store, "i1")
    store.fail_next("save_outcome", UnknownItemError("i1"))

    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(store).annotate(OUTCOME_ID, notes="Better", takeaways=())

    # Assert
    assert raised.value.item_id == "i1"


def test_rating_an_outcome_whose_item_was_deleted_meanwhile_raises_unknown_item() -> None:
    # Setup
    store = FaultyStore()
    stored_completion(store, "i1")
    store.fail_next("save_outcome", UnknownItemError("i1"))

    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(store).rate(OUTCOME_ID, 3)

    # Assert
    assert raised.value.item_id == "i1"


def test_annotating_with_nothing_to_change_is_refused_saying_what_to_give() -> None:
    # Setup
    lifecycle = a_lifecycle(store_with_an_outcome())

    # Execute
    with pytest.raises(LifecycleRefused, match=NOTHING_TO_ANNOTATE):
        lifecycle.annotate(OUTCOME_ID)


def test_annotating_with_nothing_to_change_leaves_the_stored_outcome_unchanged() -> None:
    # Setup
    store = store_with_an_outcome()
    before = fetched_outcome(store, OUTCOME_ID)

    # Execute
    with pytest.raises(LifecycleRefused):
        a_lifecycle(store).annotate(OUTCOME_ID)

    # Assert
    assert fetched_outcome(store, OUTCOME_ID) == before
