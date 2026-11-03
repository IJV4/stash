import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Self, TypeVar

from stash.domain import Item, ItemType, Stage
from stash.hermes_adapter.ports import ItemReader
from stash.store.port import DEFAULT_PAGE_SIZE

DEFAULT_LIMIT = DEFAULT_PAGE_SIZE
ECHO_LIMIT = 40
ELLIPSIS = "…"
MAX_LIMIT = 50
_SEPARATORS = re.compile(r"[\s-]+")

E = TypeVar("E", bound=StrEnum)


def _echoed(raw: str) -> str:
    text = raw.strip()
    return text if len(text) <= ECHO_LIMIT else f"{text[:ECHO_LIMIT]}{ELLIPSIS}"


def _parse_member(kind: type[E], name: str, raw: str) -> E:
    try:
        return kind(_SEPARATORS.sub("_", raw.strip().casefold()))
    except ValueError:
        valid = ", ".join(member.value for member in kind)
        raise ValueError(f"unknown {name} {_echoed(raw)!r} (valid: {valid})") from None


def _optional_member(kind: type[E], name: str, raw: object) -> E | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"{name} must be text")
    return _parse_member(kind, name, raw)


def _limit(raw: object) -> int:
    if raw is None:
        return DEFAULT_LIMIT
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("limit must be an integer")
    return raw


@dataclass(frozen=True, slots=True)
class ItemQuery:
    stage: Stage | None
    item_type: ItemType | None
    limit: int

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")

    @classmethod
    def from_text(cls, raw: str) -> Self:
        stage = _parse_member(Stage, "stage", raw) if raw.strip() else None
        return cls(stage, None, DEFAULT_LIMIT)

    @classmethod
    def from_arguments(cls, args: Mapping[str, object]) -> Self:
        return cls(
            _optional_member(Stage, "stage", args.get("stage")),
            _optional_member(ItemType, "item_type", args.get("item_type")),
            _limit(args.get("limit")),
        )

    def fetch(self, reader: ItemReader) -> list[Item]:
        return reader.list_items(stage=self.stage, item_type=self.item_type, limit=self.limit)
