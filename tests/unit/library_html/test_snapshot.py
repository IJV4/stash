import pytest
from builders import NAIVE
from fakes.store_factories import FreshStore

from stash.library_html import build_snapshot


def test_a_snapshot_cannot_be_built_at_a_moment_without_a_timezone() -> None:
    # Setup
    store = FreshStore()

    # Execute / Assert
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        build_snapshot(store, NAIVE)
