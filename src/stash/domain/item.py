import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType

from stash.domain._validation import frozen_strings, require_aware
from stash.domain.capture import RawCapture, Route

TITLE_LIMIT = 120
ELLIPSIS = "…"
UNTITLED = "Untitled"


class ItemType(StrEnum):
    PLACE = "place"
    RECIPE = "recipe"
    PURCHASE = "purchase"
    LEARN = "learn"
    BOOK = "book"
    MEDIA = "media"
    IDEA = "idea"
    PLAN = "plan"
    ACTIVITY = "activity"
    GIFT = "gift"
    OTHER = "other"

    @property
    def label(self) -> str:
        return _ITEM_TYPE_LABELS[self]


_ITEM_TYPE_LABELS = {
    ItemType.PLACE: "Places",
    ItemType.RECIPE: "Recipes",
    ItemType.PURCHASE: "Purchases",
    ItemType.LEARN: "Learning",
    ItemType.BOOK: "Books",
    ItemType.MEDIA: "Media",
    ItemType.IDEA: "Ideas",
    ItemType.PLAN: "Plans",
    ItemType.ACTIVITY: "Activities",
    ItemType.GIFT: "Gifts",
    ItemType.OTHER: "Other",
}


class Stage(StrEnum):
    INBOX = "inbox"
    WANT_TO = "want_to"
    PLANNED = "planned"
    DOING = "doing"
    DONE = "done"
    DROPPED = "dropped"

    @property
    def label(self) -> str:
        return _STAGE_LABELS[self]


_STAGE_LABELS = {
    Stage.INBOX: "Inbox",
    Stage.WANT_TO: "Want to",
    Stage.PLANNED: "Planned",
    Stage.DOING: "Doing",
    Stage.DONE: "Done",
    Stage.DROPPED: "Dropped",
}


def _require_fileable(title: str, stage: Stage, date: dt.date | None) -> None:
    if not title.strip():
        raise ValueError("title must not be blank")
    if isinstance(date, dt.datetime):
        raise ValueError("date must be a date, not a datetime")
    if stage is Stage.PLANNED and date is None:
        raise ValueError("planned items need a date")


def _freeze(filing_or_item: "Filing | Item") -> None:
    object.__setattr__(filing_or_item, "details", MappingProxyType(dict(filing_or_item.details)))
    object.__setattr__(filing_or_item, "tags", frozen_strings("tags", filing_or_item.tags))
    object.__setattr__(filing_or_item, "people", frozen_strings("people", filing_or_item.people))


@dataclass(frozen=True, slots=True)
class Filing:
    route: Route
    item_type: ItemType
    title: str
    stage: Stage
    details: Mapping[str, str]
    tags: tuple[str, ...]
    people: tuple[str, ...]
    date: dt.date | None

    def __post_init__(self) -> None:
        _require_fileable(self.title, self.stage, self.date)
        _freeze(self)


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    capture_id: str
    item_type: ItemType
    title: str
    stage: Stage
    source_url: str | None
    note: str
    details: Mapping[str, str]
    tags: tuple[str, ...]
    people: tuple[str, ...]
    date: dt.date | None
    created_at: dt.datetime
    updated_at: dt.datetime

    def __post_init__(self) -> None:
        _require_fileable(self.title, self.stage, self.date)
        require_aware("created_at", self.created_at)
        require_aware("updated_at", self.updated_at)
        _freeze(self)

    @classmethod
    def from_filing(
        cls,
        item_id: str,
        capture: RawCapture,
        filing: Filing,
        source_url: str | None,
        now: dt.datetime,
    ) -> "Item":
        return cls(
            id=item_id,
            capture_id=capture.id,
            item_type=filing.item_type,
            title=filing.title,
            stage=filing.stage,
            source_url=source_url,
            note=capture.text,
            details=filing.details,
            tags=filing.tags,
            people=filing.people,
            date=filing.date,
            created_at=now,
            updated_at=now,
        )

    def retyped(self, item_type: ItemType, now: dt.datetime) -> "Item":
        return replace(self, item_type=item_type, updated_at=now)

    def moved_to(self, stage: Stage, now: dt.datetime) -> "Item":
        return replace(self, stage=stage, updated_at=now)


def derive_title(text: str) -> str:
    for line in text.splitlines():
        collapsed = " ".join(line.split())
        if collapsed:
            return _clipped(collapsed)
    return UNTITLED


def _clipped(title: str) -> str:
    if len(title) <= TITLE_LIMIT:
        return title
    return title[: TITLE_LIMIT - len(ELLIPSIS)] + ELLIPSIS
