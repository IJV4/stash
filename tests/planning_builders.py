from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from builders import BASE, LOS_ANGELES, an_item, stored
from fakes.model_source import FakeModelSource

from stash.domain import Item, ItemType, Stage
from stash.llm import ChatModel
from stash.planning import StepProposer
from stash.store import Store

DATE_NIGHT_ID = "date-night"
DATE_NIGHT_ON = date(2027, 2, 12)
RESCHEDULED_ON = date(2027, 3, 1)


def a_date_night(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "id": DATE_NIGHT_ID,
        "title": "Date night",
        "item_type": ItemType.PLAN,
        "stage": Stage.PLANNED,
        "date": DATE_NIGHT_ON,
        "note": "Dinner and a show",
    }
    return an_item(**{**fields, **overrides})


def stored_date_night(store: Store, **overrides: Any) -> Item:
    return stored(store, a_date_night(**overrides))


def a_raw_step(**overrides: object) -> dict[str, object]:
    return {"text": "Book the table", "lead_days": 7, **overrides}


def steps_reply(count: int) -> dict[str, object]:
    return {"steps": [{"text": f"Prep step {n}", "lead_days": n} for n in range(1, count + 1)]}


def a_proposer(model: ChatModel, clock: Callable[[], datetime] = lambda: BASE) -> StepProposer:
    return StepProposer(FakeModelSource(model), clock, LOS_ANGELES)
