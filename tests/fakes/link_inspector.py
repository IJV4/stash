from collections.abc import Mapping

from stash.enrich.links import LinkInfo


class FakeLinkInspector:
    def __init__(self, infos: Mapping[str, LinkInfo] | None = None) -> None:
        self._infos = dict(infos or {})
        self.inspected: list[str] = []

    def inspect(self, url: str) -> LinkInfo:
        self.inspected.append(url)
        return self._infos.get(url) or LinkInfo.unknown(url)
