from stash.enrich.links import LinkInfo, LinkInspector
from stash.enrich.urls import WEB, platform_of


class KnownPlatformsOnly:
    def __init__(self, inner: LinkInspector) -> None:
        self._inner = inner

    def inspect(self, url: str) -> LinkInfo:
        if platform_of(url) == WEB:
            return LinkInfo.unknown(url)
        return self._inner.inspect(url)
