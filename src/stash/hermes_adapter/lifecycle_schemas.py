from typing import Any

from stash.domain import (
    DROP_REASON_LIMIT,
    MAX_RATING,
    MAX_TAKEAWAYS,
    MIN_RATING,
    MOVEABLE_STAGES,
    OUTCOME_NOTES_LIMIT,
    TAKEAWAY_LIMIT,
)
from stash.hermes_adapter.tool_schema import ITEM_TYPE, limit_property, owners_data
from stash.lifecycle import MAX_LIBRARY_LIMIT, MIN_LIBRARY_LIMIT

FIND_THE_ID = "Call stash_search (or stash_list) first to find the id."
OWNERS_DATA = owners_data("Titles, notes and details")
ITEM_ID = {"type": "string", "description": "The item's id, from stash_search."}
OUTCOME_ID = {"type": "string", "description": "The outcome's id, from stash_get."}
NOTES = {
    "type": "string",
    "maxLength": OUTCOME_NOTES_LIMIT,
    "description": "The owner's own words about it.",
}
TAKEAWAYS = {
    "type": "array",
    "items": {"type": "string", "maxLength": TAKEAWAY_LIMIT},
    "maxItems": MAX_TAKEAWAYS,
    "description": "Short separate lessons or highlights, one per entry.",
}
_MOVEABLE_STAGE_VALUES = [stage.value for stage in MOVEABLE_STAGES]


def _schema(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    parameters: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        parameters["required"] = required
    return {"name": name, "description": f"{description} {OWNERS_DATA}", "parameters": parameters}


GET_SCHEMA = _schema(
    "stash_get",
    f"Show one saved item with its link details, every outcome and the items grouped under it. "
    f"{FIND_THE_ID}",
    {"item_id": ITEM_ID},
    ["item_id"],
)

COMPLETE_SCHEMA = _schema(
    "stash_complete",
    f"Mark an item done, recording one outcome: a rating, notes and takeaways, and whether to "
    f"keep it in the library. Completing a done item again records another outcome. {FIND_THE_ID}",
    {
        "item_id": ITEM_ID,
        "rating": {
            "type": "integer",
            "minimum": MIN_RATING,
            "maximum": MAX_RATING,
            "description": "Stars.",
        },
        "notes": NOTES,
        "takeaways": TAKEAWAYS,
        "keep": {"type": "boolean", "description": "Keep it in the library."},
        "completed_on": {
            "type": "string",
            "format": "date",
            "description": "YYYY-MM-DD; today when omitted.",
        },
    },
    ["item_id"],
)

ANNOTATE_SCHEMA = _schema(
    "stash_annotate",
    "Edit an outcome. This replaces the notes, so pass the full text; takeaways are replaced "
    "only when given. Find the outcome_id with stash_get after stash_search finds the item.",
    {"outcome_id": OUTCOME_ID, "notes": NOTES, "takeaways": TAKEAWAYS},
    ["outcome_id", "notes"],
)

SET_STAGE_SCHEMA = _schema(
    "stash_set_stage",
    f"Move an item to another stage. Marking an item done is not a stage change: call "
    f"stash_complete for that. Planned needs a date. {FIND_THE_ID}",
    {
        "item_id": ITEM_ID,
        "stage": {"type": "string", "enum": _MOVEABLE_STAGE_VALUES},
        "reason": {
            "type": "string",
            "maxLength": DROP_REASON_LIMIT,
            "description": "Why it was dropped; only with stage dropped.",
        },
    },
    ["item_id", "stage"],
)

KEEP_SCHEMA = _schema(
    "stash_keep",
    f"Put a done item in the library, or take it out. {FIND_THE_ID}",
    {"item_id": ITEM_ID, "kept": {"type": "boolean"}},
    ["item_id", "kept"],
)

GROUP_SCHEMA = _schema(
    "stash_group",
    f"Group an item under a parent item, or pass a null parent_id to take it out of its group. "
    f"Groups are one level deep. {FIND_THE_ID}",
    {
        "child_id": ITEM_ID,
        "parent_id": {"type": ["string", "null"], "description": "The parent's id, or null."},
    },
    ["child_id", "parent_id"],
)

LIBRARY_SCHEMA = _schema(
    "stash_library",
    "List the kept items with their latest rating, most recently finished first.",
    {
        "item_type": ITEM_TYPE,
        "limit": limit_property(MIN_LIBRARY_LIMIT, MAX_LIBRARY_LIMIT),
    },
    [],
)
