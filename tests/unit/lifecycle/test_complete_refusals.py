from collections.abc import Callable

import pytest
from builders import (
    BARE_STRING_REFUSAL,
    BARE_STRING_TAKEAWAYS,
    NONE_TAKEAWAYS,
    an_item_at,
    fetched_item,
    stored,
)
from fakes.store_factories import FreshStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage
from stash.lifecycle import Completion, Lifecycle, LifecycleRefused, UnknownItem

REFUSED_COMPLETIONS: dict[str, Callable[[Lifecycle], Completion]] = {
    "rating-six": lambda lifecycle: lifecycle.complete("i1", rating=6),
    "bare-string-takeaways": lambda lifecycle: lifecycle.complete(
        "i1", takeaways=BARE_STRING_TAKEAWAYS
    ),
}


@pytest.mark.parametrize("complete", REFUSED_COMPLETIONS.values(), ids=REFUSED_COMPLETIONS.keys())
def test_completing_with_details_the_domain_refuses_raises_lifecycle_refused(
    complete: Callable[[Lifecycle], Completion],
) -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    with pytest.raises(LifecycleRefused):
        complete(a_lifecycle(store))


@pytest.mark.parametrize("complete", REFUSED_COMPLETIONS.values(), ids=REFUSED_COMPLETIONS.keys())
def test_a_refused_completion_leaves_the_stage_and_outcomes_unchanged(
    complete: Callable[[Lifecycle], Completion],
) -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    with pytest.raises(LifecycleRefused):
        complete(a_lifecycle(store))

    # Assert
    assert (fetched_item(store, "i1").stage, store.outcomes_for("i1")) == (Stage.DOING, [])


def test_a_refusal_carries_the_domain_message_for_the_owner() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    with pytest.raises(LifecycleRefused, match="rating must be between 1 and 5"):
        a_lifecycle(store).complete("i1", rating=6)


def test_completing_with_bare_string_takeaways_tells_the_owner_to_give_separate_items() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    with pytest.raises(LifecycleRefused, match=BARE_STRING_REFUSAL):
        a_lifecycle(store).complete("i1", takeaways=BARE_STRING_TAKEAWAYS)


def test_a_wiring_bug_in_takeaways_is_not_dressed_up_as_a_refusal() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    with pytest.raises(TypeError):
        a_lifecycle(store).complete("i1", takeaways=NONE_TAKEAWAYS)


def test_completing_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(FreshStore()).complete("nope")

    # Assert
    assert raised.value.item_id == "nope"
