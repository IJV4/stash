import http.client
import socket
from collections.abc import Callable
from dataclasses import dataclass
from threading import Thread

from threads import start

from stash.library_server import LibraryServer

LIBRARY_TOKEN = "Ab3-._~Ab3-._~Ab3-._~Ab3-"
LOOPBACK = "127.0.0.1"
ANY_FREE_PORT = 0
CLIENT_TIMEOUT_SECONDS = 3
VOLATILE_HEADERS = ("date",)


@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes
    headers: dict[str, str]


def start_serving(source: Callable[[], str]) -> tuple[LibraryServer, Thread]:
    server = LibraryServer(source, LIBRARY_TOKEN, LOOPBACK, ANY_FREE_PORT)
    thread = start(server.serve_forever)
    fetch(server.port, "/healthz")
    return server, thread


def fetch(port: int, target: str) -> Reply:
    connection = http.client.HTTPConnection(LOOPBACK, port, timeout=CLIENT_TIMEOUT_SECONDS)
    try:
        connection.request("GET", target)
        return reply_of(connection.getresponse())
    finally:
        connection.close()


def send_raw(port: int, payload: bytes) -> Reply:
    with socket.create_connection((LOOPBACK, port), CLIENT_TIMEOUT_SECONDS) as client:
        client.sendall(payload)
        response = http.client.HTTPResponse(client)
        response.begin()
        return reply_of(response)


def reply_of(response: http.client.HTTPResponse) -> Reply:
    headers = {name.lower(): value for name, value in response.getheaders()}
    for volatile in VOLATILE_HEADERS:
        headers.pop(volatile, None)
    return Reply(response.status, response.read(), headers)
