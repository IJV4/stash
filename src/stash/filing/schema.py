from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import cast

from stash.domain import ItemType, Route, Stage

SCHEMA_NAME = "filing"
FILEABLE_STAGES = (Stage.INBOX, Stage.WANT_TO, Stage.PLANNED)
DATE_PATTERN = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def _string_array() -> dict[str, object]:
    return {"type": "array", "items": {"type": "string"}}


def _enum(values: Iterable[str]) -> dict[str, object]:
    return {"type": "string", "enum": list(values)}


def _properties() -> dict[str, object]:
    return {
        "route": _enum(route.value for route in Route),
        "item_type": _enum(item_type.value for item_type in ItemType),
        "title": {"type": "string"},
        "stage": _enum(stage.value for stage in FILEABLE_STAGES),
        "details": {"type": "object", "additionalProperties": {"type": "string"}},
        "tags": _string_array(),
        "people": _string_array(),
        "date": {"type": ["string", "null"], "pattern": DATE_PATTERN},
    }


def _frozen(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def _filing_schema() -> Mapping[str, object]:
    properties = _properties()
    schema = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    return cast(Mapping[str, object], _frozen(schema))


FILING_SCHEMA = _filing_schema()
