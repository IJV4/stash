from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import httpx
from html_rig import FakeResolver, Handler, not_found, requested_url
from yt_dlp.utils import DownloadError

from stash.enrich.html_meta import HtmlMetaInspector
from stash.enrich.links import FallbackInspector
from stash.enrich.ytdlp import YtDlpInspector


def ytdlp_fails(url: str) -> Mapping[str, object]:
    raise DownloadError("unsupported URL")


@dataclass(slots=True)
class LinkRig:
    inspector: FallbackInspector
    requests: list[httpx.Request] = field(default_factory=list)
    extracted: list[str] = field(default_factory=list)

    def requested_hosts(self) -> list[str]:
        return [httpx.URL(requested_url(request)).host for request in self.requests]


def build_link_rig(
    extract: Callable[[str], Mapping[str, object]] = ytdlp_fails,
    handler: Handler = not_found,
) -> LinkRig:
    requests: list[httpx.Request] = []
    extracted: list[str] = []

    def recording_extract(url: str) -> Mapping[str, object]:
        extracted.append(url)
        return extract(url)

    def recording(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(recording))
    inspector = FallbackInspector(
        YtDlpInspector(recording_extract), HtmlMetaInspector(client, resolve=FakeResolver())
    )
    return LinkRig(inspector, requests, extracted)
