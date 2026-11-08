import logging

import pytest
from fakes.recording_page_source import PAGE, RecordingPageSource
from library_http_rig import answer, answer_raw, request_of
from library_server_rig import LIBRARY_TOKEN
from log_records import recording_logs

from stash.store import StoreBusyError

WITH_TOKEN = f"/?k={LIBRARY_TOKEN}"
COOKIE_SET = f"stash_k={LIBRARY_TOKEN}; HttpOnly; SameSite=Strict; Path=/"
WITH_COOKIE = {"Cookie": f"stash_k={LIBRARY_TOKEN}"}
LOGGER_NAME = "stash.library_server"
SECURITY_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
}
REQUEST_LINE_LIMIT = 64 * 1024
OVERLONG_REQUEST_LINE = b"GET /" + b"a" * REQUEST_LINE_LIMIT
MALFORMED_WITH_TOKEN = f"GET {WITH_TOKEN} extra HTTP/1.1\r\n\r\n".encode()
BARE_REQUEST_WITH_TOKEN = f"GET {WITH_TOKEN}\r\n".encode()
BARE_REQUEST_WITH_WRONG_TOKEN = b"GET /?k=wrong\r\n"
BUSY = StoreBusyError("locked")
BOOM = RuntimeError("boom-secret")
EVERY_KIND_OF_ANSWER = (
    (request_of("GET", WITH_TOKEN), None),
    (request_of("GET", "/nowhere"), None),
    (request_of("GET", "/healthz"), None),
    (request_of("POST", WITH_TOKEN), None),
    (request_of("GET", WITH_TOKEN), BUSY),
    (request_of("GET", WITH_TOKEN), BOOM),
    (OVERLONG_REQUEST_LINE, None),
    (MALFORMED_WITH_TOKEN, None),
    (BARE_REQUEST_WITH_TOKEN, None),
    (b"POST /x\r\n", None),
    (b"GET / HTTP/9.9\r\n\r\n", None),
)


def test_a_get_with_the_token_in_the_query_answers_the_page_and_sets_the_session_cookie() -> None:
    # Execute
    reply = answer("GET", WITH_TOKEN)

    # Assert
    assert (
        reply.status,
        reply.body,
        reply.headers["content-type"],
        reply.headers["set-cookie"],
    ) == (200, PAGE.encode(), "text/html; charset=utf-8", COOKIE_SET)


def test_a_get_with_only_the_cookie_answers_the_page_without_setting_a_cookie() -> None:
    # Execute
    reply = answer("GET", "/", headers=WITH_COOKIE)

    # Assert
    assert (reply.status, reply.body, "set-cookie" in reply.headers) == (200, PAGE.encode(), False)


@pytest.mark.parametrize("target", ["/", "/?k=wrong"])
def test_a_wrong_or_missing_token_answers_exactly_what_an_unknown_path_answers(
    target: str,
) -> None:
    # Setup
    source = RecordingPageSource()

    # Execute
    refused = answer("GET", target, source, {"Cookie": "stash_k=wrong"})
    unknown = answer("GET", "/nowhere", source)

    # Assert
    assert refused == unknown


def test_an_unknown_path_answers_a_fixed_404_with_no_cookie_and_no_hint() -> None:
    # Execute
    reply = answer("GET", "/nowhere?k=wrong")

    # Assert
    assert (reply.status, reply.body, "set-cookie" in reply.headers) == (404, b"Not Found", False)


def test_healthz_answers_ok_as_plain_text_without_a_token() -> None:
    # Execute
    reply = answer("GET", "/healthz")

    # Assert
    assert (reply.status, reply.body, reply.headers["content-type"]) == (
        200,
        b"ok",
        "text/plain; charset=utf-8",
    )


@pytest.mark.parametrize("target", ["/../etc/passwd", "/healthz/x"])
def test_an_odd_path_answers_404_and_never_asks_for_the_page(target: str) -> None:
    # Setup
    source = RecordingPageSource()

    # Execute
    reply = answer("GET", target, source, WITH_COOKIE)

    # Assert
    assert (reply.status, source.calls) == (404, 0)


@pytest.mark.parametrize("method", ["HEAD", "POST", "PUT", "DELETE", "OPTIONS", "BREW"])
def test_every_method_but_get_answers_405_allowing_get_and_never_asks_for_the_page(
    method: str,
) -> None:
    # Setup
    source = RecordingPageSource()

    # Execute
    reply = answer(method, WITH_TOKEN, source)

    # Assert
    assert (reply.status, reply.headers["allow"], source.calls) == (405, "GET", 0)


def test_a_refused_method_is_answered_and_logged_once() -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer("POST", "/")

    # Assert
    assert logs.entries() == [(logging.INFO, "POST / 405")]


def test_a_request_line_over_64_kib_answers_414() -> None:
    # Execute
    reply = answer_raw(OVERLONG_REQUEST_LINE)

    # Assert
    assert reply.status == 414


def test_a_malformed_request_line_answers_a_fixed_400_that_echoes_nothing() -> None:
    # Execute
    reply = answer_raw(MALFORMED_WITH_TOKEN)

    # Assert
    assert (reply.status, reply.body) == (400, b"Bad Request")


def test_every_answer_carries_the_security_headers() -> None:
    # Execute
    replies = [
        answer_raw(payload, RecordingPageSource(failure=f)) for payload, f in EVERY_KIND_OF_ANSWER
    ]

    # Assert
    assert [r.headers.items() >= SECURITY_HEADERS.items() for r in replies] == [True] * len(replies)


def test_every_answer_states_its_content_length() -> None:
    # Execute
    replies = [
        answer_raw(payload, RecordingPageSource(failure=f)) for payload, f in EVERY_KIND_OF_ANSWER
    ]

    # Assert
    assert [r.headers["content-length"] for r in replies] == [str(len(r.body)) for r in replies]


def test_a_locked_database_answers_503_with_a_fixed_body() -> None:
    # Execute
    reply = answer("GET", WITH_TOKEN, RecordingPageSource(failure=BUSY))

    # Assert
    assert (reply.status, reply.body) == (503, b"Service Unavailable")


def test_any_other_failure_answers_500_with_a_fixed_body_that_hides_the_error() -> None:
    # Execute
    reply = answer("GET", WITH_TOKEN, RecordingPageSource(failure=BOOM))

    # Assert
    assert (reply.status, reply.body) == (500, b"Internal Server Error")


def test_a_failed_page_is_logged_once_as_an_error_whose_message_names_no_request() -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer("GET", WITH_TOKEN, RecordingPageSource(failure=BOOM))

    # Assert
    errors = [message for level, message in logs.entries() if level == logging.ERROR]
    assert errors == ["library render failed"]


def test_the_access_log_records_the_method_the_path_without_its_query_and_the_status() -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer("GET", "/nowhere?k=wrong&x=1")

    # Assert
    assert [message for _, message in logs.entries() if "/nowhere" in message] == [
        "GET /nowhere 404"
    ]


def test_the_access_log_shows_no_control_character_from_the_path() -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer_raw(b"GET /\x1b[31mred HTTP/1.0\r\n\r\n")

    # Assert
    assert [message for _, message in logs.entries() if "red" in message] == ["GET /_[31mred 404"]


def test_a_malformed_request_line_is_logged_without_its_query() -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer_raw(MALFORMED_WITH_TOKEN)

    # Assert
    assert [message for _, message in logs.entries() if "Bad request" in message] == [
        "code 400, message Bad request syntax ('GET / extra HTTP/1.1')"
    ]


@pytest.mark.parametrize(
    ("payload", "failure"),
    [
        (request_of("GET", WITH_TOKEN), None),
        (request_of("GET", f"/x?k={LIBRARY_TOKEN}"), None),
        (request_of("GET", WITH_TOKEN), BOOM),
        (request_of("GET", WITH_TOKEN), BUSY),
        (MALFORMED_WITH_TOKEN, None),
        (request_of("GET", "/", WITH_COOKIE), None),
    ],
    ids=["page", "not-found", "failed", "busy", "malformed", "cookie"],
)
def test_the_token_and_the_query_string_never_reach_the_log(
    payload: bytes, failure: Exception | None
) -> None:
    # Setup
    with recording_logs(LOGGER_NAME) as logs:
        answer_raw(payload, RecordingPageSource(failure=failure))

    # Assert
    leaks = [m for _, m in logs.entries() if LIBRARY_TOKEN in m or "?k" in m or "=" in m]
    assert leaks == []


def test_a_bare_request_with_the_token_gets_a_full_answer_with_the_headers_and_the_cookie() -> None:
    # Execute
    reply = answer_raw(BARE_REQUEST_WITH_TOKEN)

    # Assert
    assert (
        reply.status,
        reply.headers.items() >= SECURITY_HEADERS.items(),
        reply.headers["set-cookie"],
    ) == (200, True, COOKIE_SET)


def test_a_bare_request_with_a_wrong_token_gets_the_fixed_404_with_the_headers() -> None:
    # Execute
    reply = answer_raw(BARE_REQUEST_WITH_WRONG_TOKEN)

    # Assert
    assert (reply.status, reply.body, reply.headers.items() >= SECURITY_HEADERS.items()) == (
        404,
        b"Not Found",
        True,
    )
