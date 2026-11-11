import datetime as dt
import re
from collections.abc import Iterable
from urllib.parse import SplitResult, urlsplit

HTTP_SCHEMES = frozenset({"http", "https"})
NON_PRINTABLE_PLACEHOLDER = " "
# ZWNJ and ZWJ are Cf, so isprintable() is False, yet they join emoji and Persian/Indic letters.
JOINERS = frozenset({"\u200c", "\u200d"})
_HOST_NAME = re.compile(r"[a-z0-9_.-]+")
_IPV6_LITERAL = re.compile(r"[0-9a-f:.]+")


def require_aware(name: str, moment: dt.datetime) -> None:
    if moment.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def require_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


def require_max_length(name: str, value: str, limit: int) -> None:
    if len(value) > limit:
        raise ValueError(f"{name} must be at most {limit} characters")


def require_plain_date(name: str, value: dt.date) -> None:
    if isinstance(value, dt.datetime):
        raise ValueError(f"{name} must be a date, not a datetime")


def frozen_strings(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{name} must be a collection of strings, not a single string")
    return tuple(values)


def require_safe_media_path(path: str) -> None:
    if not path.strip():
        raise ValueError("media path must not be blank")
    if "\x00" in path:
        raise ValueError("media path must not contain a NUL character")
    if "://" in path:
        raise ValueError("media path must not be a URL")
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("media path must not contain a '..' segment")


def http_url_host(value: str) -> str | None:
    if any(character.isspace() or not character.isprintable() for character in value):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    if parts.scheme not in HTTP_SCHEMES or not _has_valid_port(parts):
        return None
    return _ascii_host(parts.hostname) if parts.hostname else None


def _has_valid_port(parts: SplitResult) -> bool:
    try:
        _ = parts.port
    except ValueError:
        return False
    return True


def _ascii_host(host: str) -> str | None:
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    pattern = _IPV6_LITERAL if ":" in ascii_host else _HOST_NAME
    return ascii_host if pattern.fullmatch(ascii_host) else None


def require_http_url(name: str, value: str) -> None:
    if http_url_host(value) is None:
        raise ValueError(f"{name} must be an http(s) URL with a host")


def collapse_and_clip(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit].rstrip()


def replace_non_printable(text: str) -> str:
    if not _has_visible_character(text):
        return NON_PRINTABLE_PLACEHOLDER * len(text)
    return "".join(
        character if character.isprintable() or character in JOINERS else NON_PRINTABLE_PLACEHOLDER
        for character in text
    )


def _has_visible_character(text: str) -> bool:
    return any(character.isprintable() and not character.isspace() for character in text)


def printable_and_clip(text: str, limit: int) -> str:
    return collapse_and_clip(replace_non_printable(text), limit)
