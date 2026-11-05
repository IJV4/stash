import logging
from typing import Any

from stash.domain import Stage
from stash.hermes_adapter.ports import ItemReader
from stash.hermes_adapter.queries import MAX_LIMIT, MIN_LIMIT, ItemQuery, checked_limit
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNREADABLE, answering, items_answer
from stash.hermes_adapter.tool_schema import ITEM_TYPE, limit_property, owners_data
from stash.hermes_adapter.tool_spec import ToolSpec

logger = logging.getLogger(__name__)

QUERY_LIMIT = 200

_LIMIT_PROPERTY = limit_property(MIN_LIMIT, MAX_LIMIT)

SEARCH_SCHEMA: dict[str, Any] = {
    "name": "stash_search",
    "description": (
        "Search the owner's saved items by words in the title, note or tags, newest first. "
        + owners_data("Titles")
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Words to look for."},
            "limit": _LIMIT_PROPERTY,
        },
        "required": ["query"],
    },
}

LIST_SCHEMA: dict[str, Any] = {
    "name": "stash_list",
    "description": (
        "List the owner's saved items, newest first, optionally narrowed by stage or type. "
        + owners_data("Titles")
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": [stage.value for stage in Stage]},
            "item_type": ITEM_TYPE,
            "limit": _LIMIT_PROPERTY,
        },
    },
}


def _query_text(arguments: ToolArguments) -> str:
    text = arguments.required_text("query")
    if not text.strip():
        raise ValueError("query must not be blank")
    if len(text.strip()) > QUERY_LIMIT:
        raise ValueError(f"query must be at most {QUERY_LIMIT} characters")
    return text.strip()


class StashTools:
    def __init__(self, reader: ItemReader) -> None:
        self._reader = reader

    def specs(self) -> tuple[ToolSpec, ...]:
        return (ToolSpec(SEARCH_SCHEMA, self.search), ToolSpec(LIST_SCHEMA, self.list_items))

    def search(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._search, logger)

    def list_items(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._list, logger)

    def _search(self, arguments: ToolArguments) -> str:
        text = _query_text(arguments)
        limit = checked_limit(arguments.limit())
        return items_answer(self._reader.search_items(text, limit=limit))

    def _list(self, arguments: ToolArguments) -> str:
        return items_answer(ItemQuery.from_arguments(arguments).fetch(self._reader))
