import datetime as dt
from collections.abc import Iterable


def require_aware(name: str, moment: dt.datetime) -> None:
    if moment.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def frozen_strings(name: str, values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{name} must be a collection of strings, not a single string")
    return tuple(values)
