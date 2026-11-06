from datetime import timedelta
from typing import Any

from builders import BASE, an_item

from stash.domain import Item, Stage

DUNE_ID = "dune"
RAMEN_ID = "ramen"
CONTEXT = "2h free Saturday, at home"


def a_want_to(item_id: str = DUNE_ID, **overrides: Any) -> Item:
    fields: dict[str, Any] = {"title": item_id.title(), "stage": Stage.WANT_TO}
    return an_item(id=item_id, **{**fields, **overrides})


def a_raw_pick(
    item_id: object = DUNE_ID, reason: object = "Fits a quiet Saturday"
) -> dict[str, object]:
    return {"item_id": item_id, "reason": reason}


def picks_reply(*raw_picks: object) -> dict[str, object]:
    return {"picks": list(raw_picks)}


def want_to_items_oldest_first(count: int) -> list[Item]:
    return [
        a_want_to(f"item{n}", created_at=BASE + timedelta(minutes=n), updated_at=BASE)
        for n in range(count)
    ]
