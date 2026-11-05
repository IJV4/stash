import io
from datetime import timedelta

import pytest
from builders import BASE, stored_completion, stored_item
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.cli.commands import library, show
from stash.cli.failure import FAILURE, CommandFailed
from stash.domain import ItemType
from stash.lifecycle import LibraryQuery


def a_library() -> MemoryStore:
    store = MemoryStore()
    stored_completion(store, "dune", title="Dune", item_type=ItemType.BOOK, kept=True)
    stored_completion(
        store,
        "pad-thai",
        title="Pad thai",
        item_type=ItemType.RECIPE,
        kept=True,
        recorded_at=BASE + timedelta(minutes=1),
    )
    stored_completion(store, "skipped", title="Not kept", item_type=ItemType.BOOK, kept=False)
    return store


def library_output(query: LibraryQuery) -> str:
    out = io.StringIO()
    library(a_lifecycle(a_library()), query, out)
    return out.getvalue()


def test_library_prints_each_kept_item_with_its_id_before_its_library_line_newest_first() -> None:
    # Execute
    output = library_output(LibraryQuery())

    # Assert
    assert output == "pad-thai  📚 Recipes: Pad thai · ⭐4\ndune  📚 Books: Dune · ⭐4\n"


def test_library_narrows_to_a_type() -> None:
    # Execute
    output = library_output(LibraryQuery(ItemType.BOOK))

    # Assert
    assert output == "dune  📚 Books: Dune · ⭐4\n"


def test_library_caps_the_number_of_items_at_the_limit() -> None:
    # Execute
    output = library_output(LibraryQuery(limit=1))

    # Assert
    assert output == "pad-thai  📚 Recipes: Pad thai · ⭐4\n"


def test_library_with_nothing_kept_prints_no_items() -> None:
    # Setup
    out = io.StringIO()

    # Execute
    library(a_lifecycle(MemoryStore()), LibraryQuery(), out)

    # Assert
    assert out.getvalue() == "No items.\n"


def test_library_exits_0() -> None:
    # Execute
    exit_code = library(a_lifecycle(MemoryStore()), LibraryQuery(), io.StringIO())

    # Assert
    assert exit_code == 0


def test_show_prints_the_items_history() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="trip", title="Japan trip", item_type=ItemType.PLAN)
    stored_item(store, id="ramen", title="Tokyo ramen", parent_id="trip")
    out = io.StringIO()

    # Execute
    show(a_lifecycle(store), "trip", out)

    # Assert
    assert (
        out.getvalue()
        == "Plans · Japan trip · Inbox\nIn this group:\n  Places · Tokyo ramen · Inbox\n"
    )


def test_show_exits_0() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id="trip", title="Japan trip")

    # Execute
    exit_code = show(a_lifecycle(store), "trip", io.StringIO())

    # Assert
    assert exit_code == 0


def test_show_of_an_unknown_id_fails_with_the_lifecycle_message() -> None:
    # Execute
    with pytest.raises(CommandFailed) as failure:
        show(a_lifecycle(MemoryStore()), "nope", io.StringIO())

    # Assert
    assert (str(failure.value), failure.value.exit_code) == ("no item 'nope'", FAILURE)
