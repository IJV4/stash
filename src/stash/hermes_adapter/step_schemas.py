from functools import partial
from typing import Any

from stash.domain import MAX_LEAD_DAYS, MIN_LEAD_DAYS, STEP_TEXT_LIMIT
from stash.hermes_adapter.tool_schema import tool_schema

OWNERS_DATA_SUBJECT = "Item titles and step texts"
FIND_THE_ITEM = "Call stash_search (or stash_list) first to find the item_id."
ITEM_ID = {"type": "string", "description": "The item's id, from stash_search or stash_list."}
STEP_ID = {
    "type": "string",
    "description": "The step's id, as returned by stash_add_step, stash_edit_step or "
    "stash_complete_step; find the item with stash_search first.",
}
TEXT = {
    "type": "string",
    "maxLength": STEP_TEXT_LIMIT,
    "description": "What to do, in a few words.",
}
LEAD_DAYS = {
    "type": "integer",
    "minimum": MIN_LEAD_DAYS,
    "maximum": MAX_LEAD_DAYS,
    "description": "Days before the item's date that the step is due.",
}
DUE_ON = {
    "type": "string",
    "format": "date",
    "description": "YYYY-MM-DD; the day the step is due.",
}
ONE_DUE = "lead_days or due_on, not both"

_schema = partial(tool_schema, subject=OWNERS_DATA_SUBJECT)


ADD_STEP_SCHEMA: dict[str, Any] = _schema(
    "stash_add_step",
    f"Add a confirmed prep step to an item, last in its list. Give exactly one of lead_days or "
    f"due_on. {FIND_THE_ITEM}",
    {"item_id": ITEM_ID, "text": TEXT, "lead_days": LEAD_DAYS, "due_on": DUE_ON},
    ["item_id", "text"],
)

EDIT_STEP_SCHEMA: dict[str, Any] = _schema(
    "stash_edit_step",
    f"Change a step's text, its lead time or its date: at least one, and {ONE_DUE}. "
    f"Find the step_id in the answer of an earlier step tool.",
    {"step_id": STEP_ID, "text": TEXT, "lead_days": LEAD_DAYS, "due_on": DUE_ON},
    ["step_id"],
)

COMPLETE_STEP_SCHEMA: dict[str, Any] = _schema(
    "stash_complete_step",
    "Mark a step done; a step that was only proposed becomes confirmed too.",
    {"step_id": STEP_ID},
    ["step_id"],
)
