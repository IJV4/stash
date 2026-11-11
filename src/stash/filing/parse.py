import datetime as dt
import re
from collections.abc import Mapping

from stash.domain import (
    DETAIL_KEY_LIMIT,
    DETAIL_VALUE_LIMIT,
    MAX_DETAILS,
    Filing,
    ItemType,
    Route,
    Stage,
    collapse_and_clip,
    derive_title,
    enum_member,
    lacks_required_date,
    printable_and_clip,
    replace_non_printable,
)
from stash.filing.schema import DATE_PATTERN, FILEABLE_STAGES

TAG_LIMIT = 40
MAX_TAGS = 10
PERSON_LIMIT = 80
MAX_PEOPLE = 5
ISO_DATE = re.compile(DATE_PATTERN)


def inbox_filing(fallback_text: str, route: Route) -> Filing:
    return Filing(
        route=route,
        item_type=ItemType.OTHER,
        title=derive_title(fallback_text),
        stage=Stage.INBOX,
        details={},
        tags=(),
        people=(),
        date=None,
    )


def parse_filing(raw: Mapping[str, object], fallback_text: str) -> Filing:
    base = inbox_filing(fallback_text, enum_member(Route, raw.get("route")) or Route.UNSURE)
    date = _date(raw.get("date"))
    stage = enum_member(Stage, raw.get("stage"), FILEABLE_STAGES) or base.stage
    if lacks_required_date(stage, date):
        stage = Stage.WANT_TO
    return Filing(
        route=base.route,
        item_type=enum_member(ItemType, raw.get("item_type")) or base.item_type,
        title=_title(raw.get("title")) or base.title,
        stage=stage,
        details=_details(raw.get("details")),
        tags=_texts(raw.get("tags"), TAG_LIMIT, MAX_TAGS),
        people=_texts(raw.get("people"), PERSON_LIMIT, MAX_PEOPLE),
        date=date,
    )


def _title(value: object) -> str | None:
    if not isinstance(value, str) or not replace_non_printable(value).strip():
        return None
    return derive_title(value)


def _date(value: object) -> dt.date | None:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _details(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    pairs = (
        (collapse_and_clip(key, DETAIL_KEY_LIMIT), printable_and_clip(text, DETAIL_VALUE_LIMIT))
        for key, text in value.items()
        if isinstance(key, str) and isinstance(text, str)
    )
    return dict([(key, text) for key, text in pairs if key and text][:MAX_DETAILS])


def _texts(value: object, limit: int, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    clipped = (collapse_and_clip(item, limit) for item in value if isinstance(item, str))
    return tuple(dict.fromkeys(item for item in clipped if item))[:maximum]
