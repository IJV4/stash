import hmac
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import parse_qs

COOKIE_NAME = "stash_k"
QUERY_PARAMETER = "k"
PAGE_PATH = "/"
HEALTH_PATH = "/healthz"
COOKIE_ATTRIBUTES = "HttpOnly; SameSite=Strict; Path=/"
MAX_QUERY_FIELDS = 8


class Route(StrEnum):
    PAGE = "page"
    HEALTH = "health"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class Admission:
    granted: bool
    set_cookie: str | None = field(default=None, repr=False)


DENIED = Admission(granted=False)
GRANTED_BY_COOKIE = Admission(granted=True)


def route_of(target: str) -> Route:
    path = target.partition("?")[0]
    if path == PAGE_PATH:
        return Route.PAGE
    if path == HEALTH_PATH:
        return Route.HEALTH
    return Route.NOT_FOUND


class LibraryAccess:
    def __init__(self, token: str) -> None:
        self._token = token

    def admit(self, target: str, cookie_header: str | None) -> Admission:
        try:
            from_query = _query_values(target)
        except ValueError:
            return DENIED
        if any(self._matches(value) for value in from_query):
            return Admission(granted=True, set_cookie=self._cookie_to_set())
        if any(self._matches(value) for value in _cookie_values(cookie_header)):
            return GRANTED_BY_COOKIE
        return DENIED

    def _matches(self, presented: str) -> bool:
        return hmac.compare_digest(presented.encode(), self._token.encode())

    def _cookie_to_set(self) -> str:
        return f"{COOKIE_NAME}={self._token}; {COOKIE_ATTRIBUTES}"


def _query_values(target: str) -> list[str]:
    query = target.partition("?")[2]
    return parse_qs(query, max_num_fields=MAX_QUERY_FIELDS).get(QUERY_PARAMETER, [])


def _cookie_values(cookie_header: str | None) -> list[str]:
    pieces = (cookie_header or "").split(";")
    named = (piece.partition("=") for piece in pieces)
    return [value.strip() for name, _, value in named if name.strip() == COOKIE_NAME]
