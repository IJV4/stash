import datetime as dt
from dataclasses import dataclass
from typing import ClassVar

from stash.domain import Item, Pick, Step

FORGOTTEN_LIMIT = 3
PICK_LIMIT = 3
NEW_WINDOW = dt.timedelta(days=7)
UPCOMING_DAYS = 14


@dataclass(frozen=True, slots=True)
class UpcomingItem:
    RANK: ClassVar[int] = 0
    on: dt.date
    item: Item

    def __post_init__(self) -> None:
        if self.on != self.item.date:
            raise ValueError(f"{self.on} is not the date of {self.item.id!r}")


@dataclass(frozen=True, slots=True)
class UpcomingStep:
    RANK: ClassVar[int] = 1
    on: dt.date
    item: Item
    step: Step

    def __post_init__(self) -> None:
        if self.step.item_id != self.item.id:
            raise ValueError(f"step {self.step.id!r} belongs to item {self.step.item_id!r}")
        if self.on != self.step.due_date(self.item.date):
            raise ValueError(f"{self.on} is not the due date of step {self.step.id!r}")


UpcomingEntry = UpcomingItem | UpcomingStep


@dataclass(frozen=True, slots=True)
class DigestSections:
    new_items: tuple[Item, ...]
    forgotten: tuple[Item, ...]
    upcoming: tuple[UpcomingEntry, ...]
    picks: tuple[Pick, ...]

    def __post_init__(self) -> None:
        if len(self.forgotten) > FORGOTTEN_LIMIT:
            raise ValueError(f"a digest shows at most {FORGOTTEN_LIMIT} forgotten items")
        if len(self.picks) > PICK_LIMIT:
            raise ValueError(f"a digest shows at most {PICK_LIMIT} picks")


EMPTY_SECTIONS = DigestSections((), (), (), ())
