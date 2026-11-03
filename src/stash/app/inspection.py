from collections.abc import Callable, Mapping

import httpx

from stash.enrich.deadline import DeadlineInspector
from stash.enrich.html_meta import HtmlMetaInspector
from stash.enrich.links import FallbackInspector, LinkInspector
from stash.enrich.platform_scope import KnownPlatformsOnly
from stash.enrich.ytdlp import YtDlpInspector

INSPECTION_DEADLINE_SECONDS = 25.0


def build_inspector(
    client: httpx.Client,
    extract: Callable[[str], Mapping[str, object]],
    deadline_seconds: float = INSPECTION_DEADLINE_SECONDS,
) -> LinkInspector:
    return DeadlineInspector(
        FallbackInspector(KnownPlatformsOnly(YtDlpInspector(extract)), HtmlMetaInspector(client)),
        deadline_seconds,
    )
