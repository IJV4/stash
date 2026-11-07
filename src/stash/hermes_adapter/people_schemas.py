from functools import partial
from typing import Any

from stash.domain import (
    KEY_DATE_LABEL_LIMIT,
    MAX_ALIASES,
    PERSON_NAME_LIMIT,
    PERSON_RELATION_LIMIT,
    KeyDateKind,
)
from stash.hermes_adapter.tool_schema import tool_schema

OWNERS_DATA_SUBJECT = "Names, relations and labels"
FIND_THE_PERSON = "Call stash_people first to find the person_id."
PERSON_ID = {"type": "string", "description": "The person's id, from stash_people."}
ITEM_ID = {"type": "string", "description": "The item's id, from stash_search or stash_list."}
NAME = {
    "type": "string",
    "maxLength": PERSON_NAME_LIMIT,
    "description": "What the owner calls them.",
}
RELATION = {
    "type": "string",
    "maxLength": PERSON_RELATION_LIMIT,
    "description": "Who they are to the owner, such as wife or colleague.",
}
ALIASES = {
    "type": "array",
    "maxItems": MAX_ALIASES,
    "items": {"type": "string", "maxLength": PERSON_NAME_LIMIT},
    "description": "Other names the owner uses for them.",
}
KIND = {"type": "string", "enum": [kind.value for kind in KeyDateKind]}
MONTH = {"type": "integer", "minimum": 1, "maximum": 12}
DAY = {"type": "integer", "minimum": 1, "maximum": 31}
YEAR = {"type": "integer", "description": "The year it began (such as the birth year), if known."}
LABEL = {
    "type": "string",
    "maxLength": KEY_DATE_LABEL_LIMIT,
    "description": "What the date is, for kind other.",
}

_schema = partial(tool_schema, subject=OWNERS_DATA_SUBJECT)

PEOPLE_SCHEMA: dict[str, Any] = _schema(
    "stash_people",
    "List the people the owner keeps, soonest key date first, with each one's next key date.",
    {},
    [],
)

ADD_PERSON_SCHEMA: dict[str, Any] = _schema(
    "stash_add_person",
    "Remember a person. A name or alias another person already has is refused.",
    {"name": NAME, "relation": RELATION, "aliases": ALIASES},
    ["name"],
)

ADD_KEY_DATE_SCHEMA: dict[str, Any] = _schema(
    "stash_add_key_date",
    f"Add a yearly key date (birthday, anniversary or other) to a person. {FIND_THE_PERSON}",
    {
        "person_id": PERSON_ID,
        "kind": KIND,
        "month": MONTH,
        "day": DAY,
        "year": YEAR,
        "label": LABEL,
    },
    ["person_id", "kind", "month", "day"],
)

LINK_PERSON_SCHEMA: dict[str, Any] = _schema(
    "stash_link_person",
    f"Link a saved item, such as a gift idea, to a person. {FIND_THE_PERSON}",
    {"item_id": ITEM_ID, "person_id": PERSON_ID},
    ["item_id", "person_id"],
)

REMOVE_PERSON_SCHEMA: dict[str, Any] = _schema(
    "stash_remove_person",
    f"Forget a person and their key dates; their items stay saved. {FIND_THE_PERSON}",
    {"person_id": PERSON_ID},
    ["person_id"],
)
