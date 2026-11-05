import pytest
from builders import BASE, an_item, an_outcome, days_after, minutes_after, stored, stored_item
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.lifecycle import UnknownItem


def test_the_history_of_an_item_carries_the_stored_item() -> None:
    # Setup
    store = MemoryStore()
    item = stored_item(store, id="i1")

    # Execute
    history = a_lifecycle(store).history("i1")

    # Assert
    assert history.item == item


def test_the_history_lists_the_outcomes_oldest_first() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="i1")
    later = an_outcome(id="o-later", completed_on=days_after(5))
    earlier = an_outcome(id="o-earlier", completed_on=days_after(1))
    store.add_outcome(later)
    store.add_outcome(earlier)

    # Execute
    history = a_lifecycle(store).history("i1")

    # Assert
    assert history.outcomes == (earlier, later)


def test_the_history_lists_the_items_children() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="trip")
    first = stored(store, an_item(id="first", parent_id="trip", created_at=BASE, updated_at=BASE))
    second = stored(
        store,
        an_item(
            id="second",
            parent_id="trip",
            created_at=minutes_after(1),
            updated_at=minutes_after(1),
        ),
    )

    # Execute
    history = a_lifecycle(store).history("trip")

    # Assert
    assert history.children == (first, second)


def test_the_history_of_an_item_with_no_outcomes_or_children_is_empty() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="i1")

    # Execute
    history = a_lifecycle(store).history("i1")

    # Assert
    assert (history.outcomes, history.children) == ((), ())


def test_the_history_leaves_out_the_outcomes_and_children_of_other_items() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="i1")
    stored_item(store, id="other")
    stored_item(store, id="other-child", parent_id="other")
    store.add_outcome(an_outcome(id="o-other", item_id="other"))

    # Execute
    history = a_lifecycle(store).history("i1")

    # Assert
    assert (history.outcomes, history.children) == ((), ())


def test_the_history_of_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(MemoryStore()).history("nope")

    # Assert
    assert raised.value.item_id == "nope"
