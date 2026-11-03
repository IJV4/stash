from enum import StrEnum
from typing import TypeVar

_E = TypeVar("_E", bound=StrEnum)


def enum_member(kind: type[_E], value: object, allowed: tuple[_E, ...] | None = None) -> _E | None:
    if not isinstance(value, str):
        return None
    try:
        member = kind(value)
    except ValueError:
        return None
    return member if allowed is None or member in allowed else None
