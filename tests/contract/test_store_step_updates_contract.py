import pytest
from fakes.store_factories import StoreFactory, all_stores
from step_builders import a_step
from step_store_helpers import DUE_ON, with_items

from stash.store import DuplicateStepError, UnknownItemError


@all_stores
def test_a_saved_step_is_returned_by_get_step(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        step = a_step(lead_days=None, due_on=DUE_ON, confirmed=True)
        store.save_step(step)

        # Execute
        found = store.get_step("s1")

        # Assert
        assert found == step


@all_stores
def test_get_step_of_an_unknown_id_returns_none(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        # Execute
        found = store.get_step("missing")

        # Assert
        assert found is None


@all_stores
def test_saving_a_step_again_updates_it_in_place(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        step = a_step()
        store.save_step(step)
        store.save_step(step.confirmed_now())

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [step.confirmed_now()]


@all_stores
def test_saving_one_step_leaves_the_items_other_steps_untouched(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        sibling = a_step(id="s2", position=1)
        store.save_steps("i1", [a_step(id="s1"), sibling])

        # Execute
        store.save_step(a_step(id="s1", text="Reworded"))

        # Assert
        assert store.get_step("s2") == sibling


@all_stores
def test_saving_a_step_with_an_id_held_by_another_item_raises_duplicate_step_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        store.save_step(a_step(item_id="i1"))

        # Execute / Assert
        with pytest.raises(DuplicateStepError, match="s1"):
            store.save_step(a_step(item_id="i2"))


@all_stores
def test_refusing_a_single_step_held_by_another_item_leaves_both_items_steps_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        owned = a_step(id="s1", item_id="i1")
        sibling = a_step(id="s2", item_id="i2")
        store.save_step(owned)
        store.save_step(sibling)
        with pytest.raises(DuplicateStepError):
            store.save_step(a_step(id="s1", item_id="i2", text="Moved"))

        # Execute
        found = (store.steps_for("i1"), store.steps_for("i2"))

        # Assert
        assert found == ([owned], [sibling])


@all_stores
def test_saving_a_step_for_an_unknown_item_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        # Execute / Assert
        with pytest.raises(UnknownItemError) as refused:
            store.save_step(a_step(item_id="missing"))

        # Assert
        assert refused.value.item_id == "missing"


@all_stores
def test_saving_a_step_for_an_unknown_item_stores_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with pytest.raises(UnknownItemError):
            store.save_step(a_step(item_id="missing"))

        # Execute
        found = store.get_step("s1")

        # Assert
        assert found is None


@all_stores
def test_saving_a_step_of_an_unknown_item_whose_id_is_held_elsewhere_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_step(a_step(id="s1", item_id="i1"))

        # Execute / Assert
        with pytest.raises(UnknownItemError):
            store.save_step(a_step(id="s1", item_id="missing"))
