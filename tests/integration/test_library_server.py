import pytest
from fakes.recording_page_source import PAGE, RecordingPageSource
from library_server_rig import (
    ANY_FREE_PORT,
    LIBRARY_TOKEN,
    LOOPBACK,
    fetch,
    send_raw,
    start_serving,
)
from socket_permission import requires_local_binding
from threads import THREAD_TIMEOUT_SECONDS, run_in_thread

from stash.library_server import LibraryServer

REQUEST_LINE_LIMIT = 64 * 1024
UNTERMINATED_LINE_ONE_PAST_THE_LIMIT = (b"GET /" + b"a" * REQUEST_LINE_LIMIT)[
    : REQUEST_LINE_LIMIT + 1
]

pytestmark = [pytest.mark.integration, requires_local_binding]


def test_a_served_library_answers_the_page_over_a_real_socket() -> None:
    # Setup
    server, thread = start_serving(RecordingPageSource())

    # Execute
    reply = fetch(server.port, f"/?k={LIBRARY_TOKEN}")
    server.shutdown()
    thread.join(THREAD_TIMEOUT_SECONDS)

    # Assert
    assert (reply.status, reply.body) == (200, PAGE.encode())


def test_shutdown_ends_the_serving_loop_and_closes_the_listening_socket() -> None:
    # Setup
    server, thread = start_serving(RecordingPageSource())

    # Execute
    server.shutdown()
    thread.join(THREAD_TIMEOUT_SECONDS)

    # Assert
    assert (thread.is_alive(), _refuses_connections(server.port)) == (False, True)


def test_shutdown_of_a_server_that_never_served_returns_and_closes_the_socket() -> None:
    # Setup
    server = LibraryServer(RecordingPageSource(), LIBRARY_TOKEN, LOOPBACK, ANY_FREE_PORT)

    # Execute
    run_in_thread(server.shutdown)

    # Assert
    assert _refuses_connections(server.port)


def test_a_request_line_over_64_kib_answers_414_over_a_real_socket() -> None:
    # Setup
    server, thread = start_serving(RecordingPageSource())

    # Execute
    reply = send_raw(server.port, UNTERMINATED_LINE_ONE_PAST_THE_LIMIT)
    server.shutdown()
    thread.join(THREAD_TIMEOUT_SECONDS)

    # Assert
    assert reply.status == 414


def _refuses_connections(port: int) -> bool:
    try:
        fetch(port, "/healthz")
    except ConnectionRefusedError:
        return True
    return False
