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


class FlushCountingOutput(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.flushes = 0

    def flush(self) -> None:
        self.flushes += 1


class ServerDown(Exception):
    pass


def maker_of(servers: RecordingLibraryServers) -> Callable[[], RecordingLibraryServer]:
    library = LibraryConfig()
    return lambda: servers(lambda: "", TOKEN, library.bind, library.port)


def test_the_address_line_is_flushed_before_the_server_starts_serving() -> None:
    # Setup
    out = FlushCountingOutput()
    flushes_while_serving: list[int] = []
    servers = RecordingLibraryServers(
        while_serving=lambda: flushes_while_serving.append(out.flushes)
    )

    # Execute
    commands.serve(maker_of(servers), LibraryConfig(), out)

    # Assert
    assert flushes_while_serving == [1]


def test_the_server_is_shut_down_when_serving_fails_with_an_unexpected_error() -> None:
    # Setup
    servers = RecordingLibraryServers(serving_ends_with=ServerDown())

    # Execute
    with pytest.raises(ServerDown):
        commands.serve(maker_of(servers), LibraryConfig(), io.StringIO())

    # Assert
    assert servers.events[-1] == SHUT_DOWN
