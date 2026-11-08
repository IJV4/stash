# The single DELETE ... NOT EXISTS statement is the guard; FixHandler cannot reach the
# unguarded delete_item (port + test_architecture_unguarded_delete).
from itertools import product

import pytest
from builders import an_item, an_outcome, fetched_item, stored_item, stored_parent
from fakes.store_factories import StoreFactory, on_sqlite

from stash.domain import Stage

FLAG_NAMES = ("outcome", "child", "done", "kept")


def untouched_flag_id(flags: tuple[bool, ...]) -> str:
    names = [name for name, present in zip(FLAG_NAMES, flags, strict=True) if present]
    return "-".join(names) or "untouched"


UNTOUCHED_FLAG_COMBINATIONS = [
    pytest.param(*flags, id=untouched_flag_id(flags)) for flags in product((False, True), repeat=4)
]


@on_sqlite
def test_an_untouched_item_is_deleted_and_reported_deleted(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, store.get_item("i1")) == (True, None)


@on_sqlite
def test_an_item_with_an_outcome_is_refused_and_keeps_its_outcome(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)
        outcome = an_outcome()
        store.add_outcome(outcome)

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, store.get_item("i1") is not None, store.outcomes_for("i1")) == (
            False,
            True,
            [outcome],
        )


@on_sqlite
def test_an_item_with_a_child_is_refused_and_keeps_the_child_grouped(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        child = an_item(parent_id="p1")
        store.save_item(child)

        # Execute
        deleted = store.delete_item_if_untouched("p1")

        # Assert
        assert (deleted, store.get_item("p1") is not None, store.children_of("p1")) == (
            False,
            True,
            [child],
        )


@on_sqlite
def test_a_done_item_is_refused_and_stays_stored(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DONE)

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, store.get_item("i1")) == (False, item)


@on_sqlite
def test_a_kept_item_that_is_no_longer_done_is_refused_and_stays_stored(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.WANT_TO, kept=True)

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, fetched_item(store, "i1")) == (False, item)


@on_sqlite
def test_an_unknown_item_is_reported_not_deleted(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store)

        # Execute
        deleted = store.delete_item_if_untouched("missing")

        # Assert
        assert (deleted, store.get_item("i1") is not None) == (False, True)


@on_sqlite
def test_deleting_an_untouched_child_leaves_its_parent_stored(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_parent(store)
        store.save_item(an_item(parent_id="p1"))

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, store.get_item("p1") is not None) == (True, True)


@on_sqlite
@pytest.mark.parametrize(
    ("has_outcome", "has_child", "is_done", "is_kept"), UNTOUCHED_FLAG_COMBINATIONS
)
def test_only_an_item_with_no_outcome_no_child_not_done_and_not_kept_is_deleted(
    open_store: StoreFactory, has_outcome: bool, has_child: bool, is_done: bool, is_kept: bool
) -> None:
    # Setup
    with open_store() as store:
        item = stored_item(store, stage=Stage.DONE if is_done else Stage.WANT_TO, kept=is_kept)
        outcomes = [an_outcome()] if has_outcome else []
        for outcome in outcomes:
            store.add_outcome(outcome)
        children = [an_item(id="i2", parent_id="i1")] if has_child else []
        for child in children:
            store.save_item(child)
        untouched = not (has_outcome or has_child or is_done or is_kept)

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (
            deleted,
            store.get_item("i1"),
            store.outcomes_for("i1"),
            store.children_of("i1"),
        ) == (
            untouched,
            None if untouched else item,
            outcomes,
            children,
        )
