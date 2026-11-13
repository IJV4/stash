import ipaddress
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from types import MappingProxyType

import httpx

from stash.domain import http_url_host
from stash.enrich.links import LinkInfo
from stash.enrich.urls import is_public_address, is_public_http_url

logger = logging.getLogger(__name__)

MAX_BYTES = 512 * 1024
MAX_REDIRECTS = 3
REQUEST_TIMEOUT_SECONDS = 10.0
TOTAL_DEADLINE_SECONDS = 20.0
USER_AGENT = "Mozilla/5.0 (compatible; stash-link-preview/0.1)"
REQUEST_HEADERS = MappingProxyType(
    {
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT,
    }
)
DEFAULT_CHARSET = "utf-8"
DEFAULT_PORTS = MappingProxyType({"http": 80, "https": 443})
HOST_HEADER = "Host"
CONNECTION_HEADER = "Connection"
CLOSE_CONNECTION = "close"
SNI_EXTENSION = "sni_hostname"

Resolver = Callable[[str, int], Sequence[str]]


@dataclass(frozen=True, slots=True)
class _Pinned:
    url: httpx.URL
    headers: dict[str, str]
    extensions: dict[str, str]


class HtmlMetaInspector:
    def __init__(
        self,
        client: httpx.Client,
        *,
        resolve: Resolver,
        is_public: Callable[[str], bool] = is_public_address,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._resolve = resolve
        self._is_public = is_public
        self._monotonic = monotonic

    def inspect(self, url: str) -> LinkInfo:
        if not is_public_http_url(url):
            logger.info("page fetch skipped a non-public link: host %s", http_url_host(url))
            return LinkInfo.unknown(url)
        try:
            page = self._fetch_html(url)
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeError) as error:
            logger.warning("page fetch failed: %s", type(error).__name__)
            return LinkInfo.unknown(url)
        if page is None:
            return LinkInfo.unknown(url)
        meta = _PageMeta.parse(page)
        return LinkInfo.from_page(url, meta.title, meta.description)

    def _fetch_html(self, url: str) -> str | None:
        current = url
        expired = _Deadline(self._monotonic)
        for _ in range(MAX_REDIRECTS + 1):
            if expired():
                return None
            pinned = self._pinned(current)
            if pinned is None:
                return None
            with self._client.stream(
                "GET",
                pinned.url,
                headers={**REQUEST_HEADERS, **pinned.headers},
                extensions=pinned.extensions,
                follow_redirects=False,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                if not response.has_redirect_location:
                    return _html_text(response, expired)
                current = str(httpx.URL(current).join(response.headers["location"]))
            if not is_public_http_url(current):
                logger.info(
                    "page fetch refused a redirect to a non-public link: host %s",
                    http_url_host(current),
                )
                return None
        return None

    def _pinned(self, url: str) -> _Pinned | None:
        target = httpx.URL(url)
        if _is_literal_address(target.host):
            return _Pinned(target, {}, {}) if self._is_public(target.host) else None
        name = target.raw_host.decode("ascii")
        port = target.port or DEFAULT_PORTS[target.scheme]
        try:
            addresses = self._resolve(name, port)
        except OSError as error:
            logger.info("page fetch could not resolve host %s: %s", name, type(error).__name__)
            return None
        if not addresses or not all(self._is_public(address) for address in addresses):
            logger.info("page fetch refused host %s: it resolves to a non-public address", name)
            return None
        return _Pinned(
            target.copy_with(host=addresses[0]),
            {HOST_HEADER: target.netloc.decode("ascii"), CONNECTION_HEADER: CLOSE_CONNECTION},
            {SNI_EXTENSION: name},
        )


def _is_literal_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


class _Deadline:
    def __init__(self, monotonic: Callable[[], float]) -> None:
        self._monotonic = monotonic
        self._cutoff = monotonic() + TOTAL_DEADLINE_SECONDS

    def __call__(self) -> bool:
        passed = self._monotonic() >= self._cutoff
        if passed:
            logger.info("page fetch gave up: total deadline passed")
        return passed


def _html_text(response: httpx.Response, expired: Callable[[], bool]) -> str | None:
    if not response.is_success or "html" not in response.headers.get("content-type", "").lower():
        return None
    received = bytearray()
    for chunk in response.iter_bytes():
        received += chunk
        if expired():
            return None
        if len(received) >= MAX_BYTES:
            break
    return _decoded(bytes(received[:MAX_BYTES]), response.charset_encoding)


def _decoded(content: bytes, charset: str | None) -> str:
    try:
        return content.decode(charset or DEFAULT_CHARSET, errors="replace")
    except LookupError:
        return content.decode(DEFAULT_CHARSET, errors="replace")


class _PageMeta(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._meta: dict[str, str] = {}
        self._title_parts: list[str] = []
        self._in_title = False
        self._title_seen = False

    @classmethod
    def parse(cls, html: str) -> "_PageMeta":
        parser = cls()
        parser.feed(html)
        parser.close()
        return parser

    @property
    def title(self) -> str | None:
        return self._meta.get("og:title") or "".join(self._title_parts).strip() or None

    @property
    def description(self) -> str | None:
        return self._meta.get("og:description") or self._meta.get("description")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title" and not self._title_seen:
            self._title_seen = True
            self._in_title = True
        elif tag == "meta":
            self._remember_meta(dict(attrs))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def _remember_meta(self, attributes: dict[str, str | None]) -> None:
        key = (attributes.get("property") or attributes.get("name") or "").strip().lower()
        content = (attributes.get("content") or "").strip()
        if key and content:
            self._meta.setdefault(key, content)
