import datetime as dt
from dataclasses import dataclass

from stash.domain import Item, Step


@dataclass(frozen=True, slots=True)
class ProposedStep:
    text: str
    lead_days: int

    def as_step(self, step_id: str, item_id: str, position: int, created_at: dt.datetime) -> Step:
        return Step(
            id=step_id,
            item_id=item_id,
            text=self.text,
            lead_days=self.lead_days,
            due_on=None,
            confirmed=False,
            done=False,
            position=position,
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class Proposal:
    item: Item
    steps: tuple[Step, ...]
