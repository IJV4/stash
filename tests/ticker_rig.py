import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fakes.fake_step_proposals import FakeStepProposals
from fakes.pausing_scheduler import PausingScheduler
from fakes.scripted_deliveries import ScriptedNudges, ScriptedProposals, ScriptedRetries
from fakes.scripted_sender import ScriptedSender
from fakes.store_factories import FreshStore
from hermes_events import OWNER_ID
from hermes_rig import until
from nudge_builders import SATURDAY_MORNING
from nudge_rig import a_nudge_rig
from planning_rig import planning_over
from threads import OverlapGate, await_signal

from stash.delivery import NudgeDelivery, PendingRetryDelivery, ProposalDelivery
from stash.hermes_adapter.outbox import ReplySender
from stash.hermes_adapter.scheduler import Scheduler
from stash.hermes_adapter.ticker import Ticker
from stash.planning import ProposedStep

OWNER_CHAT = OWNER_ID
INTERVAL_S = 30.0
PROPOSED_STEPS = (ProposedStep("Book the table", 7),)


def a_ticker(
    nudges: NudgeDelivery | None = None,
    proposals: ProposalDelivery | None = None,
    sender: ReplySender | None = None,
    scheduler: Scheduler | None = None,
    retries: ScriptedRetries | PendingRetryDelivery | None = None,
    **options: Any,
) -> Ticker:
    return Ticker(
        nudges or ScriptedNudges(),
        proposals or ScriptedProposals(),
        retries or ScriptedRetries(),
        sender or ScriptedSender(),
        OWNER_CHAT,
        scheduler or PausingScheduler(),
        INTERVAL_S,
        **options,
    )


def proposals_over(store: FreshStore) -> ProposalDelivery:
    return ProposalDelivery(planning_over(store, FakeStepProposals(PROPOSED_STEPS)), store)


def a_ticker_over(store: FreshStore, sender: ReplySender) -> Ticker:
    rig = a_nudge_rig(store)
    rig.digests_before_were_sent(SATURDAY_MORNING)
    return a_ticker(
        rig.delivery, proposals_over(store), sender, PausingScheduler(start=SATURDAY_MORNING)
    )


async def run_until(ticker: Ticker, predicate: Callable[[], object]) -> None:
    task = asyncio.create_task(ticker.run_forever())
    try:
        await until(predicate)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@dataclass(frozen=True, slots=True)
class BlockedNudges:
    nudges: ScriptedNudges
    gate: OverlapGate

    async def until_inside(self) -> None:
        await asyncio.to_thread(await_signal, self.gate.entered)


def nudges_blocked_until_released() -> BlockedNudges:
    gate = OverlapGate()
    return BlockedNudges(ScriptedNudges(gate.hold), gate)
