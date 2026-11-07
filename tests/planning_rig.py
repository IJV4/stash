from collections.abc import Callable
from datetime import datetime

from builders import BASE, LOS_ANGELES
from capture_builders import sequential_ids
from planning_builders import a_proposer

from stash.llm import ChatModel
from stash.planning import Declines, Planning, StepProposals
from stash.store import Store


def planning_over(
    store: Store,
    proposals: StepProposals,
    clock: Callable[[], datetime] = lambda: BASE,
    new_id: Callable[[], str] | None = None,
) -> Planning:
    return Planning(
        store, proposals, Declines(store), new_id or sequential_ids(), clock, LOS_ANGELES
    )


def a_planning(
    store: Store,
    model: ChatModel,
    clock: Callable[[], datetime] = lambda: BASE,
    new_id: Callable[[], str] | None = None,
) -> Planning:
    return planning_over(store, a_proposer(model, clock), clock, new_id)
