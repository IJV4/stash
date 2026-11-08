import logging
import re
import socket
import threading
from collections.abc import Callable
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import BaseServer, TCPServer
from typing import Any

from stash.library_access import Admission, LibraryAccess, Route, route_of
from stash.store.port import StoreBusyError

logger = logging.getLogger(__name__)

HTML_TYPE = "text/html; charset=utf-8"
TEXT_TYPE = "text/plain; charset=utf-8"
HEALTH_BODY = "ok"
ALLOWED_METHOD = "GET"
ANSWERED_VERSION = "HTTP/1.0"
CLIENT_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.1
SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Frame-Options", "DENY"),
)
QUERY_IN_TEXT = re.compile(r"\?[^\s'\"]*")
UNPRINTABLE = re.compile(r"[^\x20-\x7e]")
UNPRINTABLE_REPLACEMENT = "_"


class LibraryRequestHandler(BaseHTTPRequestHandler):
    timeout = CLIENT_TIMEOUT_SECONDS
    protocol_version = ANSWERED_VERSION
    default_request_version = ANSWERED_VERSION
    server_version = "stash"
    sys_version = ""

    def __init__(
        self,
        access: LibraryAccess,
        snapshot_source: Callable[[], str],
        request: socket.socket,
        client_address: tuple[str, int],
        server: BaseServer,
    ) -> None:
        self._access = access
        self._snapshot_source = snapshot_source
        super().__init__(request, client_address, server)

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        if self.command != ALLOWED_METHOD:
            self._respond_status(HTTPStatus.METHOD_NOT_ALLOWED, (("Allow", ALLOWED_METHOD),))
            return False
        return True

    def do_GET(self) -> None:
        route = route_of(self._target)
        if route is Route.HEALTH:
            self._respond(HTTPStatus.OK, TEXT_TYPE, HEALTH_BODY)
            return
        admission = self._access.admit(self._target, self.headers.get("Cookie"))
        if route is Route.PAGE and admission.granted:
            self._serve_page(admission)
            return
        self._respond_status(HTTPStatus.NOT_FOUND)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        self.log_error("code %d, message %s", code, message)
        self._respond_status(HTTPStatus(code))

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        path = _printable(self._target.partition("?")[0])
        logger.info("%s %s %s", self.command or "-", path or "-", code)

    def log_message(self, format: str, *args: Any) -> None:
        logger.warning("%s", _printable(QUERY_IN_TEXT.sub("", format % args)))

    @property
    def _target(self) -> str:
        words = self.requestline.split()
        return words[1] if len(words) > 1 else ""

    def _serve_page(self, admission: Admission) -> None:
        try:
            page = self._snapshot_source()
        except StoreBusyError:
            self._respond_status(HTTPStatus.SERVICE_UNAVAILABLE)
        except Exception:
            logger.exception("library render failed")
            self._respond_status(HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            cookie = (("Set-Cookie", admission.set_cookie),) if admission.set_cookie else ()
            self._respond(HTTPStatus.OK, HTML_TYPE, page, cookie)

    def _respond_status(
        self, status: HTTPStatus, headers: tuple[tuple[str, str], ...] = ()
    ) -> None:
        self._respond(status, TEXT_TYPE, status.phrase, headers)

    def _respond(
        self,
        status: HTTPStatus,
        content_type: str,
        body: str,
        headers: tuple[tuple[str, str], ...] = (),
    ) -> None:
        payload = body.encode()
        self.send_response(status)
        for name, value in (
            *SECURITY_HEADERS,
            ("Content-Type", content_type),
            ("Content-Length", str(len(payload))),
            *headers,
        ):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)


def _printable(text: str) -> str:
    return UNPRINTABLE.sub(UNPRINTABLE_REPLACEMENT, text)


class _NameLookupFreeServer(HTTPServer):
    def server_bind(self) -> None:
        # HTTPServer.server_bind resolves the host name, which stalled 35 s on the dev Mac
        TCPServer.server_bind(self)


class LibraryServer:
    def __init__(
        self, snapshot_source: Callable[[], str], token: str, bind: str, port: int
    ) -> None:
        handler = partial(LibraryRequestHandler, LibraryAccess(token), snapshot_source)
        self._http = _NameLookupFreeServer((bind, port), handler)
        self._serving = threading.Event()

    @property
    def port(self) -> int:
        return int(self._http.server_address[1])

    def serve_forever(self) -> None:
        self._serving.set()
        self._http.serve_forever(POLL_INTERVAL_SECONDS)

    def shutdown(self) -> None:
        if self._serving.is_set():
            self._http.shutdown()
        self._http.server_close()
