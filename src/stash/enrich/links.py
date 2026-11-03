from dataclasses import dataclass
from typing import Protocol, Self

from stash.domain import collapse_and_clip, require_http_url
from stash.enrich.urls import PLATFORMS, platform_of

TITLE_LIMIT = 300
DESCRIPTION_LIMIT = 2000
UPLOADER_LIMIT = 200


@dataclass(frozen=True, slots=True)
class LinkInfo:
    url: str
    platform: str
    title: str | None
    description: str | None
    uploader: str | None
    duration_s: int | None
    has_captions: bool

    def __post_init__(self) -> None:
        require_http_url("url", self.url)
        if self.platform not in PLATFORMS:
            raise ValueError(f"platform must be one of {PLATFORMS}")
        if self.duration_s is not None and not _is_non_negative_int(self.duration_s):
            raise ValueError("duration_s must be a non-negative whole number of seconds")
        object.__setattr__(self, "title", _clamped(self.title, TITLE_LIMIT))
        object.__setattr__(self, "description", _clamped(self.description, DESCRIPTION_LIMIT))
        object.__setattr__(self, "uploader", _clamped(self.uploader, UPLOADER_LIMIT))

    @classmethod
    def unknown(cls, url: str) -> Self:
        return cls.from_page(url, None, None)

    @classmethod
    def from_page(cls, url: str, title: str | None, description: str | None) -> Self:
        return cls(
            url=url,
            platform=platform_of(url),
            title=title,
            description=description,
            uploader=None,
            duration_s=None,
            has_captions=False,
        )


class LinkInspector(Protocol):
    def inspect(self, url: str) -> LinkInfo: ...


class FallbackInspector:
    def __init__(self, first: LinkInspector, second: LinkInspector) -> None:
        self._first = first
        self._second = second

    def inspect(self, url: str) -> LinkInfo:
        info = self._first.inspect(url)
        return info if info.title is not None else self._second.inspect(url)


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _clamped(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    return collapse_and_clip(text, limit) or None
