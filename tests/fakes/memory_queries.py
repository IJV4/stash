from datetime import date, datetime
from typing import NamedTuple

from stash.domain import Item, Outcome


class Recency(NamedTuple):
    completed_on: date
    recorded_at: datetime
    outcome_id: str


def recency_of(outcome: Outcome) -> Recency:
    return Recency(outcome.completed_on, outcome.recorded_at, outcome.id)


def within(day: date, start: date | None, end: date | None) -> bool:
    return (start is None or start <= day) and (end is None or day <= end)


def mentions(item: Item, needle: str) -> bool:
    return any(needle in text.casefold() for text in (item.title, item.note, *item.tags))
