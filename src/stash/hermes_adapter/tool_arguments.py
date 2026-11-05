import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TypeVar

from stash.domain import ItemType, Stage
from stash.domain.wire import require_wire_safe_id
from stash.store.port import DEFAULT_PAGE_SIZE

ECHO_LIMIT = 40
ELLIPSIS = "…"
_SEPARATORS = re.compile(r"[\s-]+")
NOT_AN_OBJECT = "arguments must be an object"
DATE_EXAMPLE = "2026-11-05"

_E = TypeVar("_E", bound=StrEnum)


def _echoed(raw: str) -> str:
    text = raw.strip()
    return text if len(text) <= ECHO_LIMIT else f"{text[:ECHO_LIMIT]}{ELLIPSIS}"


def parse_member(kind: type[_E], name: str, raw: str) -> _E:
    try:
        return kind(_SEPARATORS.sub("_", raw.strip().casefold()))
    except ValueError:
        valid = ", ".join(member.value for member in kind)
        raise ValueError(f"unknown {name} {_echoed(raw)!r} (valid: {valid})") from None


def _not_text(name: str) -> ValueError:
    return ValueError(f"{name} must be text")


@dataclass(frozen=True, slots=True)
class ToolArguments:
    values: Mapping[str, object]

    @classmethod
    def of(cls, args: object) -> "ToolArguments":
        if not isinstance(args, dict):
            raise ValueError(NOT_AN_OBJECT)
        return cls(args)

    def required_id(self, name: str) -> str:
        value = self.required_text(name)
        require_wire_safe_id(name, value)
        return value

    def nullable_id(self, name: str) -> str | None:
        if name not in self.values:
            raise ValueError(f"{name} is required (an id, or null)")
        return None if self.values[name] is None else self.required_id(name)

    def required_text(self, name: str) -> str:
        value = self.values.get(name)
        if not isinstance(value, str):
            raise _not_text(name)
        return value

    def optional_text(self, name: str) -> str:
        return "" if self.values.get(name) is None else self.required_text(name)

    def optional_reason(self) -> str | None:
        return None if self.values.get("reason") is None else self.required_text("reason")

    def optional_rating(self) -> int | None:
        return self._optional_int("rating")

    def optional_takeaways(self) -> tuple[str, ...] | None:
        takeaways = self.values.get("takeaways")
        if takeaways is None:
            return None
        if not isinstance(takeaways, list | tuple) or not all(
            isinstance(takeaway, str) for takeaway in takeaways
        ):
            raise ValueError("takeaways must be a list of text")
        return tuple(takeaways)

    def required_bool(self, name: str) -> bool:
        value = self.values.get(name)
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false")
        return value

    def optional_bool(self, name: str) -> bool | None:
        return None if self.values.get(name) is None else self.required_bool(name)

    def optional_date(self, name: str) -> date | None:
        if self.values.get(name) is None:
            return None
        text = self.required_text(name)
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            parsed = None
        if parsed is None or parsed.isoformat() != text:
            raise ValueError(f"{name} must be a date like {DATE_EXAMPLE}")
        return parsed

    def stage(self) -> Stage:
        return parse_member(Stage, "stage", self.required_text("stage"))

    def optional_stage(self) -> Stage | None:
        return self._optional_member(Stage, "stage")

    def optional_item_type(self) -> ItemType | None:
        return self._optional_member(ItemType, "item_type")

    def limit(self) -> int:
        limit = self._optional_int("limit")
        return DEFAULT_PAGE_SIZE if limit is None else limit

    def _optional_int(self, name: str) -> int | None:
        value = self.values.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError(f"{name} must be an integer")
        return value

    def _optional_member(self, kind: type[_E], name: str) -> _E | None:
        if self.values.get(name) is None:
            return None
        return parse_member(kind, name, self.required_text(name))
