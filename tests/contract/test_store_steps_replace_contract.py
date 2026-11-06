import pytest
from builders import BASE, PLUS_FIVE
from fakes.store_factories import StoreFactory, all_stores
from step_builders import a_step
from step_store_helpers import DUE_ON, ids_of, with_items

from stash.store import DuplicateStepError, UnknownItemError


@all_stores
def test_steps_saved_for_an_item_with_a_lead_time_read_back_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        step = a_step(lead_days=14, due_on=None)
        store.save_steps("i1", [step])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [step]


@all_stores
def test_steps_saved_with_an_absolute_date_read_back_unchanged(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        step = a_step(lead_days=None, due_on=DUE_ON)
        store.save_steps("i1", [step])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [step]


@all_stores
def test_a_confirmed_done_step_reads_back_confirmed_and_done(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(confirmed=True, done=True)])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert [(step.confirmed, step.done) for step in found] == [(True, True)]


@all_stores
def test_an_unconfirmed_open_step_reads_back_unconfirmed_and_open(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(confirmed=False, done=False)])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert [(step.confirmed, step.done) for step in found] == [(False, False)]


@all_stores
def test_a_step_created_in_another_offset_reads_back_at_the_same_instant(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(created_at=BASE.astimezone(PLUS_FIVE))])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert [step.created_at for step in found] == [BASE]


@all_stores
def test_saving_steps_replaces_the_items_earlier_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1"), a_step(id="s2", position=1)])
        store.save_steps("i1", [a_step(id="s3")])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert ids_of(found) == ["s3"]


@all_stores
def test_replaced_steps_can_no_longer_be_fetched_by_id(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1")])
        store.save_steps("i1", [a_step(id="s3")])

        # Execute
        found = store.get_step("s1")

        # Assert
        assert found is None


@all_stores
def test_saving_no_steps_clears_the_items_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step()])
        store.save_steps("i1", [])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == []


@all_stores
def test_saving_steps_for_an_item_leaves_other_items_steps_untouched(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        other = a_step(id="s9", item_id="i2")
        store.save_steps("i2", [other])

        # Execute
        store.save_steps("i1", [a_step(id="s1")])

        # Assert
        assert store.steps_for("i2") == [other]


@all_stores
def test_saving_steps_with_an_id_held_by_another_item_raises_duplicate_step_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        store.save_steps("i1", [a_step(id="s1", item_id="i1")])

        # Execute / Assert
        with pytest.raises(DuplicateStepError, match="s1"):
            store.save_steps("i2", [a_step(id="s1", item_id="i2", text="Moved")])


@all_stores
def test_refusing_a_step_id_held_by_another_item_leaves_both_items_steps_unchanged(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        owned = a_step(id="s1", item_id="i1")
        earlier = a_step(id="s2", item_id="i2")
        store.save_steps("i1", [owned])
        store.save_steps("i2", [earlier])
        with pytest.raises(DuplicateStepError):
            store.save_steps(
                "i2", [a_step(id="s3", item_id="i2"), a_step(id="s1", item_id="i2", position=1)]
            )

        # Execute
        found = (store.steps_for("i1"), store.steps_for("i2"))

        # Assert
        assert found == ([owned], [earlier])


@all_stores
def test_saving_steps_for_an_unknown_item_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        # Execute / Assert
        with pytest.raises(UnknownItemError) as refused:
            store.save_steps("missing", [a_step(item_id="missing")])

        # Assert
        assert refused.value.item_id == "missing"


@all_stores
def test_saving_no_steps_for_an_unknown_item_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store, pytest.raises(UnknownItemError):
        # Execute / Assert
        store.save_steps("missing", [])


@all_stores
def test_saving_steps_for_an_unknown_item_stores_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with pytest.raises(UnknownItemError):
            store.save_steps("missing", [a_step(item_id="missing")])

        # Execute
        found = store.get_step("s1")

        # Assert
        assert found is None


@all_stores
def test_saving_steps_with_a_repeated_id_keeps_the_earlier_steps(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        earlier = a_step(id="s9")
        store.save_steps("i1", [earlier])
        with pytest.raises(ValueError, match="s1"):
            store.save_steps("i1", [a_step(), a_step(position=1)])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [earlier]


@all_stores
def test_saving_a_step_of_another_item_keeps_the_earlier_steps(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1", "i2")
        earlier = a_step(id="s1")
        store.save_steps("i1", [earlier])
        with pytest.raises(ValueError, match="i2"):
            store.save_steps("i1", [a_step(id="s2"), a_step(id="s3", item_id="i2")])

        # Execute
        found = store.steps_for("i1")

        # Assert
        assert found == [earlier]


@all_stores
def test_saving_steps_of_an_unknown_item_whose_id_is_held_elsewhere_raises_unknown_item_error(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        with_items(store, "i1")
        store.save_steps("i1", [a_step(id="s1", item_id="i1")])

        # Execute / Assert
        with pytest.raises(UnknownItemError):
            store.save_steps("missing", [a_step(id="s1", item_id="missing")])
