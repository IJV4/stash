from collections.abc import Sequence
from datetime import date, datetime

from stash.domain import Item, Outcome, Person, Step, require_aware
from stash.store.port import DuplicateNameError

RANGE_ORDER_MESSAGE = "start must not be after end"


def require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def require_date_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError(RANGE_ORDER_MESSAGE)


def require_instant_range(start: datetime, end: datetime) -> None:
    require_aware("start", start)
    require_aware("end", end)
    if start > end:
        raise ValueError(RANGE_ORDER_MESSAGE)


def require_parent(child: Item) -> str:
    if child.parent_id is None:
        raise ValueError(f"item {child.id!r} has no parent to be grouped under")
    return child.parent_id


def require_outcome_for_item(item: Item, outcome: Outcome) -> None:
    if outcome.item_id != item.id:
        raise ValueError(f"outcome {outcome.id!r} is for item {outcome.item_id!r}, not {item.id!r}")


def require_steps_for_item(item_id: str, steps: Sequence[Step]) -> None:
    seen: set[str] = set()
    for step in steps:
        if step.item_id != item_id:
            raise ValueError(f"step {step.id!r} is for item {step.item_id!r}, not {item_id!r}")
        if step.id in seen:
            raise ValueError(f"step id {step.id!r} is repeated")
        seen.add(step.id)


def require_distinct_names(person: Person, others: Sequence[Person]) -> None:
    for other in others:
        if other.id != person.id and person.shares_a_name_with(other):
            raise DuplicateNameError(person, other)


def find_named(people: Sequence[Person], name: str) -> Person | None:
    return next((person for person in people if person.answers_to(name)), None)
