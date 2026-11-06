from datetime import date

from builders import stored_item

from stash.domain import Step
from stash.store import Store

DUE_ON = date(2026, 12, 24)


def with_items(store: Store, *item_ids: str) -> None:
    for item_id in item_ids:
        stored_item(store, id=item_id, title=item_id)


def ids_of(steps: list[Step]) -> list[str]:
    return [step.id for step in steps]
