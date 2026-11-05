import pytest
from builders import (
    LATER,
    PLANNED_FOR,
    an_item,
    an_item_at,
    fetched_item,
    stored,
)
from fakes.memory_store import MemoryStore
from lifecycle_rig import a_lifecycle

from stash.domain import PLANNED_NEEDS_DATE, Stage
from stash.lifecycle import LifecycleRefused, UnknownItem

REASON_ONLY_FOR_DROPPING = "a reason is only for dropping an item"
DONE_REFUSAL = "done is reached by completing an item"
BLANK_REASONS = ["", "   ", None]
STAGES_WITHOUT_A_REASON = (Stage.INBOX, Stage.WANT_TO, Stage.DOING)


def test_setting_a_stage_moves_the_item_and_stores_it() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.INBOX))

    # Execute
    moved = a_lifecycle(store, clock=lambda: LATER).set_stage("i1", Stage.DOING)

    # Assert
    assert (moved.stage, moved.updated_at, fetched_item(store, "i1")) == (
        Stage.DOING,
        LATER,
        moved,
    )


def test_setting_planned_on_an_item_with_a_date_moves_it() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item(date=PLANNED_FOR))

    # Execute
    moved = a_lifecycle(store).set_stage("i1", Stage.PLANNED)

    # Assert
    assert (moved.stage, moved.date) == (Stage.PLANNED, PLANNED_FOR)


def test_setting_dropped_with_a_reason_stores_it_dropped_with_that_reason() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    dropped = a_lifecycle(store).set_stage("i1", Stage.DROPPED, "too expensive")

    # Assert
    assert (dropped.stage, dropped.drop_reason, fetched_item(store, "i1")) == (
        Stage.DROPPED,
        "too expensive",
        dropped,
    )


@pytest.mark.parametrize("reason", BLANK_REASONS)
def test_setting_dropped_without_a_real_reason_stores_no_reason(reason: str | None) -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    dropped = a_lifecycle(store).set_stage("i1", Stage.DROPPED, reason)

    # Assert
    assert (dropped.stage, dropped.drop_reason) == (Stage.DROPPED, None)


@pytest.mark.parametrize("stage", STAGES_WITHOUT_A_REASON)
def test_a_reason_with_a_stage_other_than_dropped_is_refused_and_changes_nothing(
    stage: Stage,
) -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused, match=REASON_ONLY_FOR_DROPPING):
        a_lifecycle(store).set_stage("i1", stage, "too expensive")

    # Assert
    assert fetched_item(store, "i1") == original


@pytest.mark.parametrize("reason", ["", "   "])
def test_a_blank_reason_with_a_stage_other_than_dropped_is_ignored(reason: str) -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.INBOX))

    # Execute
    moved = a_lifecycle(store).set_stage("i1", Stage.WANT_TO, reason)

    # Assert
    assert moved.stage is Stage.WANT_TO


def test_setting_done_is_refused_pointing_at_completion_and_changes_nothing() -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused, match=DONE_REFUSAL):
        a_lifecycle(store).set_stage("i1", Stage.DONE)

    # Assert
    assert fetched_item(store, "i1") == original


def test_setting_planned_on_an_item_without_a_date_is_refused_and_changes_nothing() -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused, match=PLANNED_NEEDS_DATE):
        a_lifecycle(store).set_stage("i1", Stage.PLANNED)

    # Assert
    assert fetched_item(store, "i1") == original


def test_setting_the_stage_of_an_unknown_item_raises_unknown_item_naming_it() -> None:
    # Execute
    with pytest.raises(UnknownItem) as raised:
        a_lifecycle(MemoryStore()).set_stage("nope", Stage.DOING)

    # Assert
    assert raised.value.item_id == "nope"


def test_setting_a_stage_on_a_dropped_item_clears_its_drop_reason() -> None:
    # Setup
    store = MemoryStore()
    stored(store, an_item_at(Stage.DROPPED, drop_reason="too expensive"))

    # Execute
    moved = a_lifecycle(store).set_stage("i1", Stage.WANT_TO)

    # Assert
    assert moved.drop_reason is None


def test_a_reason_with_stage_done_is_refused_for_the_reason_and_changes_nothing() -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused, match=REASON_ONLY_FOR_DROPPING):
        a_lifecycle(store).set_stage("i1", Stage.DONE, "too expensive")

    # Assert
    assert fetched_item(store, "i1") == original


def test_a_reason_with_stage_planned_on_a_dated_item_is_refused_and_changes_nothing() -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item(date=PLANNED_FOR))

    # Execute
    with pytest.raises(LifecycleRefused, match=REASON_ONLY_FOR_DROPPING):
        a_lifecycle(store).set_stage("i1", Stage.PLANNED, "too expensive")

    # Assert
    assert fetched_item(store, "i1") == original


@pytest.mark.parametrize("reason", BLANK_REASONS)
def test_a_blank_or_missing_reason_with_stage_done_is_refused_pointing_at_completion(
    reason: str | None,
) -> None:
    # Setup
    store = MemoryStore()
    original = stored(store, an_item_at(Stage.WANT_TO))

    # Execute
    with pytest.raises(LifecycleRefused, match=DONE_REFUSAL):
        a_lifecycle(store).set_stage("i1", Stage.DONE, reason)

    # Assert
    assert fetched_item(store, "i1") == original
