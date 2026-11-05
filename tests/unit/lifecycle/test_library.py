from builders import an_item, an_outcome, days_after, stored, stored_completion
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import ItemType, Stage
from stash.lifecycle import LibraryQuery


def ids_of(store: MemoryStore, query: LibraryQuery | None = None) -> list[str]:
    lifecycle = a_lifecycle(store)
    entries = lifecycle.library() if query is None else lifecycle.library(query)
    return [entry.item.id for entry in entries]


def test_the_library_is_empty_when_nothing_is_kept() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "i1")

    # Execute
    entries = a_lifecycle(store).library()

    # Assert
    assert entries == ()


def test_the_library_lists_kept_items_with_their_last_outcome() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "i1", kept=True)

    # Execute
    [entry] = a_lifecycle(store).library()

    # Assert
    assert (entry.item.id, entry.last_outcome) == ("i1", store.outcomes_for("i1")[0])


def test_the_library_pairs_an_item_with_its_latest_outcome_not_its_first() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "i1", kept=True)
    store.add_outcome(an_outcome(id="later", item_id="i1", completed_on=days_after(3), rating=5))

    # Execute
    [entry] = a_lifecycle(store).library()

    # Assert
    assert entry.rating == 5


def test_the_library_lists_the_most_recently_finished_item_first() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "old", completed_on=days_after(0), kept=True)
    stored_completion(store, "new", completed_on=days_after(5), kept=True)

    # Execute
    listed = ids_of(store)

    # Assert
    assert listed == ["new", "old"]


def test_the_library_lists_only_the_requested_type() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "dune", item_type=ItemType.BOOK, kept=True)
    stored_completion(store, "ramen", item_type=ItemType.RECIPE, kept=True)

    # Execute
    listed = ids_of(store, LibraryQuery(ItemType.BOOK))

    # Assert
    assert listed == ["dune"]


def test_the_library_lists_at_most_the_requested_number_of_items() -> None:
    # Setup
    store = MemoryStore()
    for day, item_id in enumerate(("a", "b", "c")):
        stored_completion(store, item_id, completed_on=days_after(day), kept=True)

    # Execute
    listed = ids_of(store, LibraryQuery(limit=2))

    # Assert
    assert listed == ["c", "b"]


def test_a_kept_item_that_was_dropped_is_not_in_the_library() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(stage=Stage.DROPPED, kept=True))

    # Execute
    listed = ids_of(store)

    # Assert
    assert listed == []


def test_a_kept_item_without_an_outcome_is_listed_without_one() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(stage=Stage.DONE, kept=True))

    # Execute
    [entry] = a_lifecycle(store).library()

    # Assert
    assert entry.last_outcome is None
