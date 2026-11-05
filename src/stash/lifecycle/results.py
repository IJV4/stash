from dataclasses import dataclass
from datetime import date

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


@dataclass(frozen=True, slots=True)
class LibraryEntry:
    item: Item
    last_outcome: Outcome | None

    @property
    def rating(self) -> int | None:
        return None if self.last_outcome is None else self.last_outcome.rating

    @property
    def completed_on(self) -> date | None:
        return None if self.last_outcome is None else self.last_outcome.completed_on
