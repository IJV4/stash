import io
from collections.abc import Callable

import pytest
from fakes.recording_library_servers import (
    SHUT_DOWN,
    RecordingLibraryServer,
    RecordingLibraryServers,
)

from stash.cli import commands
from stash.config import LibraryConfig

TOKEN = "SECRETtokenSECRETtokenSECRET1"


class ServerDown(Exception):
    pass


def maker_of(servers: RecordingLibraryServers) -> Callable[[], RecordingLibraryServer]:
    library = LibraryConfig()
    return lambda: servers(lambda: "", TOKEN, library.bind, library.port)


def test_the_server_is_shut_down_when_serving_fails_with_an_unexpected_error() -> None:
    # Setup
    servers = RecordingLibraryServers(serving_ends_with=ServerDown())

    # Execute
    with pytest.raises(ServerDown):
        commands.serve(maker_of(servers), LibraryConfig(), io.StringIO())

    # Assert
    assert servers.events[-1] == SHUT_DOWN
