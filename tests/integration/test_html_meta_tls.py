import shutil
import ssl
import subprocess
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest

from stash.enrich.html_meta import HtmlMetaInspector
from stash.enrich.links import LinkInfo

LOOPBACK = "127.0.0.1"
PAGE_HOST = "preview.example.test"
OTHER_HOST = "other.example.test"
OPENSSL_SELF_SIGNED = ("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1")
PAGE = b"<html><head><title>Pinned ramen</title></head></html>"

pytestmark = pytest.mark.integration


class _PageHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, format: str, *args: object) -> None:
        return


def _certificate_for(name: str, directory: Path) -> Path:
    if shutil.which("openssl") is None:
        pytest.skip("openssl is not installed")
    certificate, key = directory / f"{name}.pem", directory / f"{name}.key"
    subprocess.run(
        [
            *OPENSSL_SELF_SIGNED,
            *("-subj", f"/CN={name}", "-addext", f"subjectAltName=DNS:{name}"),
            *("-keyout", str(key), "-out", str(certificate)),
        ],
        check=True,
        capture_output=True,
    )
    return certificate


@pytest.fixture
def serving(tmp_path: Path) -> Iterator[Callable[[str], tuple[int, Path]]]:
    servers: list[HTTPServer] = []

    def serve(certificate_name: str) -> tuple[int, Path]:
        certificate = _certificate_for(certificate_name, tmp_path)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, tmp_path / f"{certificate_name}.key")
        try:
            server = HTTPServer((LOOPBACK, 0), _PageHandler)
        except OSError:
            pytest.skip("the sandbox forbids binding a socket")
        server.socket = context.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return server.server_port, certificate

    yield serve
    for server in servers:
        server.shutdown()
        server.server_close()


def _inspect_page_host(port: int, trusted: Path) -> LinkInfo:
    client = httpx.Client(verify=ssl.create_default_context(cafile=str(trusted)))
    inspector = HtmlMetaInspector(
        client, resolve=lambda host, _port: [LOOPBACK], is_public=lambda address: True
    )
    with client:
        return inspector.inspect(f"https://{PAGE_HOST}:{port}/")


def test_the_certificate_is_checked_against_the_name_and_the_connection_goes_to_the_pin(
    serving: Callable[[str], tuple[int, Path]],
) -> None:
    # Setup
    port, certificate = serving(PAGE_HOST)

    # Execute
    info = _inspect_page_host(port, certificate)

    # Assert
    assert info.title == "Pinned ramen"


def test_a_certificate_issued_for_another_name_makes_the_page_unknown(
    serving: Callable[[str], tuple[int, Path]],
) -> None:
    # Setup
    port, certificate = serving(OTHER_HOST)

    # Execute
    info = _inspect_page_host(port, certificate)

    # Assert
    assert info == LinkInfo.unknown(f"https://{PAGE_HOST}:{port}/")
