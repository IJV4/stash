import httpx
import pytest
from http_wire import Wire

from stash.config import LibraryConfig
from stash.library_server_probe import LibraryServerProbe


def probe_of(outcome: httpx.Response | Exception, library: LibraryConfig) -> LibraryServerProbe:
    return LibraryServerProbe(library, Wire(outcome).client())


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(404, text="ok"),
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(200, text="<html>router login</html>"),
    ],
    ids=["not-found", "unavailable", "another-body"],
)
def test_anything_but_a_200_ok_fails(answer: httpx.Response) -> None:
    # Execute
    result = probe_of(answer, LibraryConfig()).check()

    # Assert
    assert result.ok is False
