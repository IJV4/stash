from itertools import groupby

import pytest
from app_builders import an_app
from fakes.snapshot_watching_store import OPENED, READ, RELEASED, SnapshotWatchingStore

TOKEN = "SECRETtokenSECRETtokenSECRET1"


class ReadFailed(Exception):
    pass


def runs_of(store: SnapshotWatchingStore) -> list[str]:
    return [event for event, _ in groupby(store.events)]


def test_the_read_snapshot_is_released_when_rendering_fails() -> None:
    # Setup
    store = SnapshotWatchingStore(read_failure=ReadFailed("database is closed"))
    app = an_app(store=store)

    # Execute
    with pytest.raises(ReadFailed):
        app.serve_only_library_page()

    # Assert
    assert runs_of(store) == [OPENED, READ, RELEASED]
