from collections.abc import Mapping
from types import MappingProxyType
from typing import cast


def frozen_schema(schema: Mapping[str, object]) -> Mapping[str, object]:
    return cast(Mapping[str, object], _frozen(schema))


def _frozen(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value
