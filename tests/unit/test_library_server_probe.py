import httpx
import pytest
from http_wire import FIVE_SECONDS, Wire

from stash.config import LibraryConfig
from stash.library_server_probe import LibraryServerProbe

NOT_RUNNING = (
    "not running; start it with stash serve or systemctl --user enable --now stash-serve.service"
)
ANSWERING = httpx.Response(200, text="ok")


def probe_of(outcome: httpx.Response | Exception, library: LibraryConfig) -> LibraryServerProbe:
    return LibraryServerProbe(library, Wire(outcome).client())


def test_a_library_server_answering_ok_passes_naming_the_port() -> None:
    # Execute
    result = probe_of(ANSWERING, LibraryConfig(port=9000)).check()

    # Assert
    assert (result.ok, result.detail) == (True, "answering on port 9000")


def test_a_refused_connection_fails_with_how_to_start_the_server() -> None:
    # Execute
    result = probe_of(httpx.ConnectError("connection refused"), LibraryConfig()).check()

    # Assert
    assert (result.ok, result.detail) == (False, NOT_RUNNING)


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


@pytest.mark.parametrize(
    ("bind", "host"),
    [("0.0.0.0", "127.0.0.1"), ("192.168.1.5", "192.168.1.5")],
    ids=["every-interface-asks-loopback", "specific-bind-as-is"],
)
def test_the_probe_asks_healthz_on_the_configured_port(bind: str, host: str) -> None:
    # Setup
    wire = Wire(ANSWERING)

    # Execute
    LibraryServerProbe(LibraryConfig(bind=bind, port=9000), wire.client()).check()

    # Assert
    assert str(wire.request.url) == f"http://{host}:9000/healthz"


def test_the_probe_passes_a_five_second_timeout_with_the_request() -> None:
    # Setup
    wire = Wire(ANSWERING)

    # Execute
    LibraryServerProbe(LibraryConfig(), wire.client()).check()

    # Assert
    assert wire.request.extensions["timeout"] == FIVE_SECONDS
