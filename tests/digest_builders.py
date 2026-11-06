from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from builders import in_los_angeles, stored
from fakes.fake_pick_source import FakePickSource
from nudge_builders import (
    FRIDAY,
    LONG_AGO,
    SATURDAY,
    a_nudge_schedule,
    a_planned_date_night,
    a_same_day_step,
    a_stuck_book,
    stored_step,
)
from suggestion_builders import a_want_to

from stash.domain import Item, Pick, Step
from stash.nudges import StuckItem, WeeklyDigest
from stash.nudges.digest import DigestSections, UpcomingEntry, UpcomingItem, UpcomingStep
from stash.nudges.digest_builder import DigestBuilder
from stash.nudges.ports import DigestStore, PickSource
from stash.store import Store

DIGEST_DAY = date(2027, 2, 7)
DIGEST_AT = in_los_angeles(DIGEST_DAY, 10).astimezone(UTC)
ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(days=7)
SAIL_ID = "sail"
SAIL_REASON = "Saturday looks free and you wanted something outdoors."


def a_new_want_to(item_id: str, days_before_digest: int, **overrides: Any) -> Item:
    created = DIGEST_AT - timedelta(days=days_before_digest)
    return a_want_to(item_id, **{"created_at": created, "updated_at": created, **overrides})


def a_forgotten_want_to(item_id: str = SAIL_ID, **overrides: Any) -> Item:
    fields: dict[str, Any] = {"created_at": LONG_AGO, "updated_at": LONG_AGO}
    return a_want_to(item_id, **{**fields, **overrides})


def a_forgotten_sail() -> Item:
    return a_forgotten_want_to(SAIL_ID, title="Learn to sail")


def a_step_the_day_before_the_date_night() -> Step:
    return a_same_day_step(lead_days=1)


def a_digest_builder(
    store: DigestStore,
    picks: PickSource | None = None,
    **config_overrides: object,
) -> DigestBuilder:
    return DigestBuilder(store, picks or FakePickSource(), a_nudge_schedule(**config_overrides))


def a_due_digest(at: datetime = DIGEST_AT, *stuck: Item) -> WeeklyDigest:
    return WeeklyDigest(at, tuple(StuckItem(item, at) for item in stuck))


def building(store: DigestStore, at: datetime = DIGEST_AT, **config: object) -> DigestSections:
    return a_digest_builder(store, **config).build(a_due_digest(at), at).sections


def some_want_tos(count: int, prefix: str = "item", title: str | None = None) -> tuple[Item, ...]:
    return tuple(
        a_want_to(f"{prefix}{n}", title=title or f"{prefix.title()} {n}") for n in range(count)
    )


def some_stuck(count: int, title: str | None = None) -> tuple[Item, ...]:
    return tuple(a_stuck_book(id=f"stuck{n}", title=title or f"Book {n}") for n in range(count))


def an_item_entry(
    item_id: str = "dinner", title: str = "Date night", day: date = SATURDAY
) -> UpcomingItem:
    item = a_planned_date_night(id=item_id, title=title, date=day)
    return UpcomingItem(day, item)


def a_step_entry(text: str = "Book the table", title: str = "Date night") -> UpcomingStep:
    item = a_planned_date_night(title=title)
    step = a_same_day_step(text=text, lead_days=1, item_id=item.id)
    return UpcomingStep(FRIDAY, item, step)


def some_item_entries(count: int, title: str | None = None) -> tuple[UpcomingItem, ...]:
    return tuple(an_item_entry(f"entry{n}", title or f"Event {n}", SATURDAY) for n in range(count))


def some_picks(count: int, title: str | None = None) -> tuple[Pick, ...]:
    return tuple(Pick(item, SAIL_REASON) for item in some_want_tos(count, "pick", title))


def a_digest_with(
    new_items: Sequence[Item] = (),
    forgotten: Sequence[Item] = (),
    upcoming: Sequence[UpcomingEntry] = (),
    picks: Sequence[Pick] = (),
    stuck: Sequence[Item] = (),
) -> WeeklyDigest:
    sections = DigestSections(tuple(new_items), tuple(forgotten), tuple(upcoming), tuple(picks))
    return WeeklyDigest(DIGEST_AT, tuple(StuckItem(item, DIGEST_AT) for item in stuck), sections)


def stored_every_section(store: Store) -> None:
    stored(store, a_new_want_to("carbonara", 2, title="Pasta carbonara"))
    stored(store, a_new_want_to("ramen", 3, title="Ramen"))
    stored(store, a_forgotten_sail())
    stored(store, a_planned_date_night())
    stored_step(store, a_step_the_day_before_the_date_night())
    stored(store, a_stuck_book())
