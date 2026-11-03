import logging
import math
from collections.abc import Callable, Mapping
from types import MappingProxyType

from stash.domain import http_url_host
from stash.enrich.links import LinkInfo
from stash.enrich.urls import is_public_http_url, platform_of

logger = logging.getLogger(__name__)

YTDLP_OPTIONS: Mapping[str, object] = MappingProxyType(
    {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 15,
    }
)


def default_ytdlp_extract(url: str) -> Mapping[str, object]:
    import yt_dlp

    with yt_dlp.YoutubeDL(dict(YTDLP_OPTIONS)) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info) if info is not None else {}


def info_to_link(url: str, info: Mapping[str, object]) -> LinkInfo:
    return LinkInfo(
        url=url,
        platform=platform_of(url),
        title=_text(info.get("title")),
        description=_text(info.get("description")),
        uploader=_text(info.get("uploader")) or _text(info.get("channel")),
        duration_s=_whole_seconds(info.get("duration")),
        has_captions=_has_entries(info.get("subtitles"))
        or _has_entries(info.get("automatic_captions")),
    )


class YtDlpInspector:
    def __init__(self, extract: Callable[[str], Mapping[str, object]]) -> None:
        self._extract = extract

    def inspect(self, url: str) -> LinkInfo:
        if not is_public_http_url(url):
            logger.info("yt-dlp skipped a non-public link: host %s", http_url_host(url))
            return LinkInfo.unknown(url)
        try:
            info = self._extract(url)
        # Third-party extractors raise arbitrary errors and inspect() promises never to raise.
        except Exception as error:
            logger.warning("yt-dlp extraction failed: %s", type(error).__name__)
            return LinkInfo.unknown(url)
        return info_to_link(url, info)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _whole_seconds(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return int(value) if value >= 0 else None


def _has_entries(value: object) -> bool:
    return isinstance(value, Mapping) and bool(value)
