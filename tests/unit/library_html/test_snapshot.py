import pytest
from builders import NAIVE, stored_completion
from fakes.memory_store import MemoryStore
from fakes.outcome_querying_store import OutcomeQueryingStore
from library_html_rig import LOCAL_NOW

from stash.domain import Stage
from stash.library_html import build_snapshot


def test_a_snapshot_cannot_be_built_at_a_moment_without_a_timezone() -> None:
    # Setup
    store = MemoryStore()

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        build_snapshot(store, NAIVE)


def test_the_outcomes_of_a_dropped_item_are_never_fetched_for_the_done_section() -> None:
    # Setup
    store = OutcomeQueryingStore()
    stored_completion(store, "film")
    stored_completion(store, "gone", stage=Stage.DROPPED)

    # Execute
    build_snapshot(store, LOCAL_NOW)

    # Assert
    assert store.outcome_queries == ["film"]
