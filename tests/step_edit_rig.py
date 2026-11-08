from datetime import date, timedelta

from builders import BASE
from fakes.fake_step_proposals import FakeStepProposals
from fakes.store_factories import FreshStore
from planning_builders import DATE_NIGHT_ID, stored_date_night
from planning_rig import planning_over
from step_builders import a_step

from stash.domain import Step
from stash.planning import Planning

LATER = BASE + timedelta(hours=1)
NEW_DAY = date(2027, 2, 1)


def date_night_with(store: FreshStore, *steps: Step) -> Planning:
    stored_date_night(store)
    store.save_steps(DATE_NIGHT_ID, list(steps))
    return planning_over(store, FakeStepProposals(), lambda: LATER)


def existing(step_id: str = "s1", position: int = 0, **overrides: object) -> Step:
    return a_step(id=step_id, item_id=DATE_NIGHT_ID, position=position, **overrides)


def proposed(step_id: str, position: int) -> Step:
    return existing(step_id, position, confirmed=False)


def confirmed(step_id: str, position: int) -> Step:
    return existing(step_id, position, confirmed=True)
