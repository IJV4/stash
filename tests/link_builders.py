from typing import Any

from stash.enrich.links import LinkInfo

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"


def a_link_info(**overrides: Any) -> LinkInfo:
    fields: dict[str, Any] = {
        "url": VIDEO_URL,
        "platform": "youtube",
        "title": "Ramen crawl",
        "description": "Five bowls in one night",
        "uploader": "Hana Eats",
        "duration_s": 61,
        "has_captions": True,
    }
    return LinkInfo(**{**fields, **overrides})
