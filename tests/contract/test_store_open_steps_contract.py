from builders import an_item_at, stored, stored_item
from fakes.store_factories import StoreFactory, all_stores
from step_builders import a_step
from step_store_helpers import ids_of, with_items

from stash.domain import Stage


@all_stores
def test_steps_read_back_in_position_order(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps(
            "i1",
            [a_step(id="s1", position=2), a_step(id="s2", position=0), a_step(id="s3", position=1)],
        )

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert ids_of(found) == ["s2", "s3", "s1"]


@all_stores
def test_steps_at_the_same_position_read_back_in_id_order(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="sb", position=0), a_step(id="sa", position=0)])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert ids_of(found) == ["sa", "sb"]


@all_stores
def test_steps_for_an_item_without_steps_is_empty(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == []


@all_stores
def test_steps_for_an_unknown_item_is_empty(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.steps_for("missing")

        # Assert
        assert found == []


@all_stores
def test_open_confirmed_steps_returns_confirmed_steps_that_are_not_done(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1", confirmed=True, done=False)])

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert ids_of(found) == ["s1"]


@all_stores
def test_open_confirmed_steps_leaves_out_unconfirmed_proposals(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1", confirmed=False, done=False)])

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert found == []


@all_stores
def test_open_confirmed_steps_leaves_out_done_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1", confirmed=True, done=True)])

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert found == []


@all_stores
def test_open_confirmed_steps_leaves_out_unconfirmed_done_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1", confirmed=False, done=True)])

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert found == []


@all_stores
def test_open_confirmed_steps_includes_steps_of_items_in_any_stage(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        for position, stage in enumerate(Stage):
            stored(store, an_item_at(stage, id=f"i{position}", title=stage.value))
            store.save_step(a_step(id=f"s{position}", item_id=f"i{position}", confirmed=True))

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert ids_of(found) == [f"s{position}" for position in range(len(Stage))]


@all_stores
def test_open_confirmed_steps_are_ordered_by_item_id_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "ia", "ib")
        store.save_step(a_step(id="s1", item_id="ib", position=0, confirmed=True))
        store.save_step(a_step(id="s2", item_id="ia", position=5, confirmed=True))

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert ids_of(found) == ["s2", "s1"]


@all_stores
def test_open_confirmed_steps_of_one_item_are_ordered_by_position(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_step(a_step(id="s1", position=2, confirmed=True))
        store.save_step(a_step(id="s2", position=1, confirmed=True))

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert ids_of(found) == ["s2", "s1"]


@all_stores
def test_open_confirmed_steps_at_the_same_position_are_ordered_by_id(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_step(a_step(id="sb", position=0, confirmed=True))
        store.save_step(a_step(id="sa", position=0, confirmed=True))

        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert ids_of(found) == ["sa", "sb"]


@all_stores
def test_open_confirmed_steps_is_empty_when_there_are_no_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.open_confirmed_steps()

        # Assert
        assert found == []


@all_stores
def test_deleting_an_untouched_item_still_succeeds_when_it_has_steps(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step()])

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert deleted is True


@all_stores
def test_an_item_with_a_confirmed_step_is_refused_and_keeps_the_step(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        step = a_step(confirmed=True)
        store.save_steps("i1", [step])

        # Execute
        deleted = store.delete_item_if_untouched("i1")

        # Assert
        assert (deleted, store.get_item("i1") is not None, store.steps_for("i1")) == (
            False,
            True,
            [step],
        )


@all_stores
def test_deleting_an_untouched_item_deletes_its_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step()])
        store.delete_item_if_untouched("i1")

        # Execute
        found = store.get_step("s1")

        # Assert
        assert found is None


@all_stores
def test_deleting_an_untouched_item_leaves_other_items_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        kept = a_step(id="s2", item_id="i2")
        store.save_steps("i1", [a_step()])
        store.save_steps("i2", [kept])
        store.delete_item_if_untouched("i1")

        # Execute
        found = store.steps_for("i2")

        # Assert
        assert found == [kept]


@all_stores
def test_a_refused_delete_keeps_the_items_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        stored_item(store, kept=True)
        step = a_step()
        store.save_steps("i1", [step])
        store.delete_item_if_untouched("i1")

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [step]
