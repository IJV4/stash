import http.client
from collections.abc import Mapping

from fakes.in_memory_connection import InMemoryConnection
from fakes.recording_page_source import RecordingPageSource
from library_server_rig import LIBRARY_TOKEN, Reply, reply_of

from stash.library_access import LibraryAccess
from stash.library_server import LibraryRequestHandler

CLIENT_ADDRESS = ("127.0.0.1", 0)
NO_SERVER = object()


def answer(
    method: str,
    target: str,
    source: RecordingPageSource | None = None,
    headers: Mapping[str, str] | None = None,
) -> Reply:
    return answer_raw(request_of(method, target, headers), source)


def request_of(method: str, target: str, headers: Mapping[str, str] | None = None) -> bytes:
    lines = [
        f"{method} {target} HTTP/1.1",
        *(f"{name}: {value}" for name, value in (headers or {}).items()),
    ]
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


def answer_raw(payload: bytes, source: RecordingPageSource | None = None) -> Reply:
    connection = InMemoryConnection(payload)
    LibraryRequestHandler(
        LibraryAccess(LIBRARY_TOKEN),
        source or RecordingPageSource(),
        connection,
        CLIENT_ADDRESS,
        NO_SERVER,
    )
    response = http.client.HTTPResponse(InMemoryConnection(connection.response))
    response.begin()
    return reply_of(response)
