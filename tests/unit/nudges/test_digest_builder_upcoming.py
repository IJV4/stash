from datetime import date, datetime, timedelta

import pytest
from builders import stored
from digest_builders import DIGEST_AT, DIGEST_DAY, a_digest_builder, a_due_digest
from fakes.store_factories import FreshStore
from nudge_builders import (
    a_same_day_step,
    a_step_due_on,
    an_undated_date_night,
    stored_step,
)

from stash.domain import Stage
from stash.nudges.digest import UPCOMING_DAYS, UpcomingStep

LAST_DAY = DIGEST_DAY + timedelta(days=UPCOMING_DAYS)
ONE_DAY = timedelta(days=1)
WINDOW_EDGES = [
    (DIGEST_DAY - ONE_DAY, False),
    (DIGEST_DAY, True),
    (LAST_DAY, True),
    (LAST_DAY + ONE_DAY, False),
]
Entry = tuple[date, str, str | None]


def upcoming(store: FreshStore, now: datetime = DIGEST_AT) -> list[Entry]:
    entries = a_digest_builder(store).build(a_due_digest(DIGEST_AT), now).sections.upcoming
    return [(e.on, e.item.id, e.step.id if isinstance(e, UpcomingStep) else None) for e in entries]


def stored_item_with_step_due_on(
    store: FreshStore, day: date, item_id: str = "plan", step_id: str = "step", **item: object
) -> None:
    stored(store, an_undated_date_night(id=item_id, **item))
    stored_step(store, a_step_due_on(day, id=step_id, item_id=item_id))


@pytest.mark.parametrize("stage", [Stage.DONE, Stage.DROPPED])
def test_a_step_of_a_closed_item_is_not_coming_up(stage: Stage) -> None:
    # Setup
    store = FreshStore()
    stored_item_with_step_due_on(store, DIGEST_DAY, stage=stage)

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []


def test_a_step_counted_from_an_undated_item_is_not_coming_up() -> None:
    # Setup
    store = FreshStore()
    stored(store, an_undated_date_night(id="plan"))
    stored_step(store, a_same_day_step(item_id="plan", lead_days=2))

    # Execute
    entries = upcoming(store)

    # Assert
    assert entries == []
