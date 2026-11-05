from datetime import UTC, date, datetime

import pytest
from builders import BASE, COMPLETED_ON, NON_DONE_STAGES, an_item_at, stored
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import Stage


@pytest.mark.parametrize("stage", NON_DONE_STAGES)
def test_completing_an_item_in_any_other_stage_leaves_it_done_unkept_and_not_a_repeat(
    stage: Stage,
) -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(stage))

    # Execute
    done = a_lifecycle(store).complete("i1")

    # Assert
    assert (done.item.stage, done.item.kept, done.repeat) == (Stage.DONE, False, False)


@pytest.mark.parametrize("keep", [True, False])
def test_completing_with_keep_sets_kept_on_the_new_done_item(keep: bool) -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    done = a_lifecycle(store).complete("i1", keep=keep)

    # Assert
    assert (done.item.stage, done.item.kept, done.repeat) == (Stage.DONE, keep, False)


def test_completing_a_reopened_kept_item_without_keep_leaves_it_kept() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.WANT_TO, kept=True))

    # Execute
    done = a_lifecycle(store).complete("i1")

    # Assert
    assert (done.item.stage, done.item.kept, done.repeat) == (Stage.DONE, True, False)


def test_completing_stores_the_done_item_and_its_outcome_together() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    done = a_lifecycle(store).complete("i1", rating=4)

    # Assert
    assert (store.get_item("i1"), store.outcomes_for("i1")) == (done.item, [done.outcome])


def test_completing_stamps_the_item_with_the_clock() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))
    now = BASE.replace(hour=15)

    # Execute
    done = a_lifecycle(store, clock=lambda: now).complete("i1")

    # Assert
    assert done.item.updated_at == now


def test_completing_records_the_rating_notes_and_takeaways_given() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    done = a_lifecycle(store).complete("i1", rating=5, notes="Loved it", takeaways=["a", "b"])

    # Assert
    assert (done.outcome.rating, done.outcome.notes, done.outcome.takeaways) == (
        5,
        "Loved it",
        ("a", "b"),
    )


def test_completing_without_details_records_an_unrated_outcome_with_no_notes_or_takeaways() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    done = a_lifecycle(store).complete("i1")

    # Assert
    assert (done.outcome.rating, done.outcome.notes, done.outcome.takeaways) == (None, "", ())


def test_the_outcome_takes_its_id_from_the_id_source_and_belongs_to_the_item() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    done = a_lifecycle(store, new_id=lambda: "outcome-7").complete("i1")

    # Assert
    assert (done.outcome.id, done.outcome.item_id) == ("outcome-7", "i1")


def test_the_outcome_is_recorded_at_the_clock_time_and_has_not_been_edited() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))
    now = BASE.replace(hour=15)

    # Execute
    done = a_lifecycle(store, clock=lambda: now).complete("i1")

    # Assert
    assert (done.outcome.recorded_at, done.outcome.edited_at) == (now, None)


def test_the_outcome_is_dated_with_the_date_given() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))

    # Execute
    done = a_lifecycle(store).complete("i1", on=COMPLETED_ON.replace(day=1))

    # Assert
    assert done.outcome.completed_on == COMPLETED_ON.replace(day=1)


def test_the_outcome_defaults_to_the_owners_local_date_not_the_utc_date() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DOING))
    just_after_midnight_in_utc = datetime(2026, 11, 3, 5, 0, tzinfo=UTC)

    # Execute
    done = a_lifecycle(store, clock=lambda: just_after_midnight_in_utc).complete("i1")

    # Assert
    assert done.outcome.completed_on == date(2026, 11, 2)
