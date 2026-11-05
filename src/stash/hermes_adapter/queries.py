from dataclasses import dataclass
from typing import Self

from stash.domain import Item, ItemType, Stage
from stash.hermes_adapter.ports import ItemReader
from stash.hermes_adapter.tool_arguments import ToolArguments, parse_member
from stash.store.port import DEFAULT_PAGE_SIZE

DEFAULT_LIMIT = DEFAULT_PAGE_SIZE
MIN_LIMIT = 1
MAX_LIMIT = 50


def checked_limit(limit: int) -> int:
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}")
    return limit


def item_type_from_text(raw: str) -> ItemType | None:
    return parse_member(ItemType, "item_type", raw) if raw.strip() else None


@dataclass(frozen=True, slots=True)
class ItemQuery:
    stage: Stage | None
    item_type: ItemType | None
    limit: int

    def __post_init__(self) -> None:
        checked_limit(self.limit)

    @classmethod
    def from_text(cls, raw: str) -> Self:
        stage = parse_member(Stage, "stage", raw) if raw.strip() else None
        return cls(stage, None, DEFAULT_LIMIT)

    @classmethod
    def from_arguments(cls, arguments: ToolArguments) -> Self:
        return cls(arguments.optional_stage(), arguments.optional_item_type(), arguments.limit())

    def fetch(self, reader: ItemReader) -> list[Item]:
        return reader.list_items(stage=self.stage, item_type=self.item_type, limit=self.limit)
