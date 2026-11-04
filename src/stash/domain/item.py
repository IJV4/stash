import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType

from stash.domain._validation import (
    frozen_strings,
    require_aware,
    require_http_url,
    require_max_length,
    require_plain_date,
    require_text,
)
from stash.domain.capture import RawCapture, Route
from stash.domain.wire import require_wire_safe_id

TITLE_LIMIT = 120
ELLIPSIS = "…"
UNTITLED = "Untitled"
DROP_REASON_LIMIT = 300
GROUPS_ONE_LEVEL_DEEP = "groups are one level deep"
OWN_PARENT = f"{GROUPS_ONE_LEVEL_DEEP}: an item cannot be its own parent"
DROP_REASON_ONLY_WHEN_DROPPED = "drop_reason is only for dropped items"


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


MOVEABLE_STAGES = (Stage.INBOX, Stage.WANT_TO, Stage.PLANNED, Stage.DOING, Stage.DROPPED)
PLANNED_NEEDS_DATE = "planned items need a date"


def lacks_required_date(stage: Stage, date: dt.date | None) -> bool:
    return stage is Stage.PLANNED and date is None


def _require_fileable(title: str, stage: Stage, date: dt.date | None) -> None:
    require_text("title", title)
    if date is not None:
        require_plain_date("date", date)
    if lacks_required_date(stage, date):
        raise ValueError(PLANNED_NEEDS_DATE)


def _require_drop_reason_fits(stage: Stage, drop_reason: str | None) -> None:
    if drop_reason is None:
        return
    if stage is not Stage.DROPPED:
        raise ValueError(DROP_REASON_ONLY_WHEN_DROPPED)
    require_text("drop_reason", drop_reason)
    require_max_length("drop_reason", drop_reason, DROP_REASON_LIMIT)


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
    kept: bool = False
    parent_id: str | None = None
    drop_reason: str | None = None

    def __post_init__(self) -> None:
        require_wire_safe_id("item id", self.id)
        require_wire_safe_id("item capture id", self.capture_id)
        if self.parent_id is not None:
            require_wire_safe_id("item parent id", self.parent_id)
            if self.parent_id == self.id:
                raise ValueError(OWN_PARENT)
        _require_drop_reason_fits(self.stage, self.drop_reason)
        _require_fileable(self.title, self.stage, self.date)
        require_aware("created_at", self.created_at)
        require_aware("updated_at", self.updated_at)
        if self.source_url is not None:
            require_http_url("source_url", self.source_url)
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
        drop_reason = self.drop_reason if stage is Stage.DROPPED else None
        return replace(self, stage=stage, drop_reason=drop_reason, updated_at=now)

    def completed(self, now: dt.datetime) -> "Item":
        if self.stage is Stage.DONE:
            raise ValueError("item is already done")
        return self.moved_to(Stage.DONE, now)

    def reopened(self, now: dt.datetime) -> "Item":
        if self.stage is not Stage.DONE:
            raise ValueError("only done items can be reopened")
        return self.moved_to(Stage.WANT_TO, now)

    def dropped(self, reason: str | None, now: dt.datetime) -> "Item":
        return replace(self.moved_to(Stage.DROPPED, now), drop_reason=reason)

    def kept_as(self, kept: bool, now: dt.datetime) -> "Item":
        # Unkeeping is allowed at any stage: a reopened item stays kept until unkept
        if kept and self.stage is not Stage.DONE:
            raise ValueError("only done items can be kept")
        return replace(self, kept=kept, updated_at=now)

    def grouped_under(self, parent: "Item", now: dt.datetime) -> "Item":
        if parent.parent_id is not None:
            raise ValueError(GROUPS_ONE_LEVEL_DEEP)
        return replace(self, parent_id=parent.id, updated_at=now)

    def ungrouped(self, now: dt.datetime) -> "Item":
        return replace(self, parent_id=None, updated_at=now)

    def can_move_to(self, stage: Stage) -> bool:
        return stage in MOVEABLE_STAGES and not lacks_required_date(stage, self.date)

    def moveable_stages(self) -> tuple[Stage, ...]:
        return tuple(stage for stage in MOVEABLE_STAGES if self.can_move_to(stage))

    def summary_line(self) -> str:
        return f"{self.item_type.label} · {self.title}"


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
