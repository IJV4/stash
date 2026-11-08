from itertools import groupby

import pytest
from app_builders import an_app
from config_builders import a_stash_config
from fakes.recording_library_servers import RecordingLibraryServers
from fakes.snapshot_watching_store import OPENED, READ, RELEASED, SnapshotWatchingStore

from stash.config import LibraryConfig
from stash.store import StoreBusyError

TOKEN = "SECRETtokenSECRETtokenSECRET1"


class ReadFailed(Exception):
    pass


def with_a_token(**overrides: object) -> dict[str, object]:
    return {"config": a_stash_config(library=LibraryConfig(token=TOKEN)), **overrides}


def runs_of(store: SnapshotWatchingStore) -> list[str]:
    return [event for event, _ in groupby(store.events)]


def test_the_read_snapshot_is_released_when_rendering_fails() -> None:
    # Setup
    store = SnapshotWatchingStore(read_failure=ReadFailed("database is closed"))
    app = an_app(store=store)

    # Execute
    with pytest.raises(ReadFailed):
        app.library_page()

    # Assert
    assert runs_of(store) == [OPENED, READ, RELEASED]


def test_a_busy_store_passes_through_the_library_page_unchanged() -> None:
    # Setup
    busy = StoreBusyError()
    app = an_app(store=SnapshotWatchingStore(busy=busy))

    # Execute / Assert
    with pytest.raises(StoreBusyError) as raised:
        app.library_page()
    assert raised.value is busy


def test_the_server_is_given_a_page_source_that_renders_inside_one_read_snapshot() -> None:
    # Setup
    store = SnapshotWatchingStore()
    servers = RecordingLibraryServers()
    app = an_app(**with_a_token(store=store, library_servers=servers))

    # Execute
    app.library_server()
    servers.created[0].snapshot_source()

    # Assert
    assert runs_of(store) == [OPENED, READ, RELEASED]
