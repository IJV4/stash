import socket
from collections.abc import Callable, Mapping, Sequence

import httpx

from stash.enrich.deadline import DeadlineInspector
from stash.enrich.html_meta import HtmlMetaInspector, Resolver
from stash.enrich.links import FallbackInspector, LinkInspector
from stash.enrich.platform_scope import KnownPlatformsOnly
from stash.enrich.ytdlp import YtDlpInspector

INSPECTION_DEADLINE_SECONDS = 25.0


def build_inspector(
    client: httpx.Client,
    extract: Callable[[str], Mapping[str, object]],
    resolve: Resolver,
    deadline_seconds: float = INSPECTION_DEADLINE_SECONDS,
) -> LinkInspector:
    return DeadlineInspector(
        FallbackInspector(
            KnownPlatformsOnly(YtDlpInspector(extract)), HtmlMetaInspector(client, resolve=resolve)
        ),
        deadline_seconds,
    )


def system_resolver(host: str, port: int) -> Sequence[str]:
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(dict.fromkeys(str(answer[4][0]) for answer in answers))
