from dataclasses import dataclass
from typing import Self

from stash.domain import Item, ItemType, Stage
from stash.hermes_adapter.ports import ItemReader
from stash.hermes_adapter.tool_arguments import ToolArguments, echoed, parse_member
from stash.store.port import DEFAULT_PAGE_SIZE

DEFAULT_LIMIT = DEFAULT_PAGE_SIZE
MIN_LIMIT = 1
MAX_LIMIT = 50
UNKNOWN_TYPE = "unknown type {raw!r} (try: {labels})"
_ITEM_TYPES_BY_NAME = {
    name.casefold(): item_type
    for item_type in ItemType
    for name in (item_type.value, item_type.label)
}
_TYPE_LABELS = ", ".join(item_type.label.casefold() for item_type in ItemType)


def checked_limit(limit: int) -> int:
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}")
    return limit


def item_type_from_text(raw: str) -> ItemType | None:
    text = raw.strip().casefold()
    if not text:
        return None
    item_type = _ITEM_TYPES_BY_NAME.get(text)
    if item_type is None:
        raise ValueError(UNKNOWN_TYPE.format(raw=echoed(raw), labels=_TYPE_LABELS))
    return item_type


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
