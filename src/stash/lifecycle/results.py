from dataclasses import dataclass

from stash.domain import Item, Outcome


@dataclass(frozen=True, slots=True)
class Completion:
    item: Item
    outcome: Outcome
    repeat: bool


@dataclass(frozen=True, slots=True)
class ItemHistory:
    item: Item
    outcomes: tuple[Outcome, ...]
    children: tuple[Item, ...]
