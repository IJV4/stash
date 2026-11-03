import datetime as dt
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path, PurePath
from typing import TypeVar

from stash.domain import ItemType, Route, Stage, enum_member
from stash.enrich import LinkInfo, platform_of
from stash.evaluation.expectation import Expectation


class Fields:
    def __init__(self, raw: object, what: str) -> None:
        if not isinstance(raw, dict):
            raise ValueError(f"{what} must be a JSON object")
        self._remaining: dict[str, object] = dict(raw)
        self._what = what

    def required(self, key: str) -> object:
        if key not in self._remaining:
            raise ValueError(f"{self._what} is missing key {key!r}")
        return self._remaining.pop(key)

    def optional(self, key: str) -> object:
        return self._remaining.pop(key, None)

    def finish(self) -> None:
        if self._remaining:
            raise ValueError(f"{self._what} has unknown key {next(iter(self._remaining))!r}")


def parse_expectation(raw: object) -> Expectation:
    fields = Fields(raw, "expect")
    expectation = Expectation(
        route=member(Route, fields.required("route"), "route"),
        item_type=_optional_member(ItemType, fields.optional("item_type"), "item_type"),
        stage=_optional_member(Stage, fields.optional("stage"), "stage"),
        date=_optional_date(fields.optional("date")),
        details=_details(fields.optional("details")),
    )
    fields.finish()
    return expectation


def parse_link(raw: object) -> LinkInfo | None:
    if raw is None:
        return None
    fields = Fields(raw, "link")
    url = text_of(fields.required("url"), "url")
    link = LinkInfo(
        url=url,
        platform=platform_of(url),
        title=optional_text_of(fields.optional("title"), "title"),
        description=optional_text_of(fields.optional("description"), "description"),
        uploader=optional_text_of(fields.optional("uploader"), "uploader"),
        duration_s=_optional_whole_number(fields.optional("duration_s")),
        has_captions=_flag(fields.optional("has_captions")),
    )
    fields.finish()
    return link


def parse_image_path(raw: object, directory: Path) -> Path | None:
    name = optional_text_of(raw, "image")
    if name is None:
        return None
    relative = PurePath(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("image must be a path inside the cases directory")
    return directory / name


_E = TypeVar("_E", bound=StrEnum)


def member(kind: type[_E], raw: object, name: str) -> _E:
    parsed = enum_member(kind, raw)
    if parsed is None:
        raise ValueError(f"{name} {raw!r} is not one of {[option.value for option in kind]}")
    return parsed


def _optional_member(kind: type[_E], raw: object, name: str) -> _E | None:
    return None if raw is None else member(kind, raw, name)


def text_of(raw: object, name: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"{name} must be a string")
    return raw


def optional_text_of(raw: object, name: str) -> str | None:
    return None if raw is None else text_of(raw, name)


def _optional_whole_number(raw: object) -> int | None:
    if raw is None or (isinstance(raw, int) and not isinstance(raw, bool)):
        return raw
    raise ValueError("duration_s must be a whole number")


def _flag(raw: object) -> bool:
    if raw is None:
        return False
    if not isinstance(raw, bool):
        raise ValueError("has_captions must be true or false")
    return raw


def _optional_date(raw: object) -> dt.date | None:
    if raw is None:
        return None
    try:
        return dt.date.fromisoformat(text_of(raw, "date"))
    except ValueError as error:
        raise ValueError("date must be YYYY-MM-DD") from error


def _details(raw: object) -> Mapping[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise ValueError("details must map text to text")
    return raw
