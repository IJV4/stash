import datetime as dt
import logging
from collections.abc import Callable

from stash.capture import Reply, proposal_reply
from stash.domain import Item, Stage
from stash.planning import Planning, PlanningRefused
from stash.store.port import Store

logger = logging.getLogger(__name__)

PROPOSAL_SCAN_LIMIT = 200
MAX_PROPOSALS_PER_TICK = 3
PROPOSAL_FAILED_LOG = "step proposal failed (%s); left for the next tick"
PROPOSAL_SEND_FAILED_LOG = "proposal send failed (%s); proposed steps withdrawn"
PROPOSAL_WITHDRAW_FAILED_LOG = "withdrawing unsent proposed steps failed (%s); steps left in place"


class ProposalDelivery:
    def __init__(self, planning: Planning, items: Store) -> None:
        self._planning = planning
        self._items = items

    def deliver(self, send: Callable[[Reply], None]) -> None:
        for item, day in self._needing_a_proposal()[:MAX_PROPOSALS_PER_TICK]:
            self._propose(item, day, send)

    def _needing_a_proposal(self) -> list[tuple[Item, dt.date]]:
        planned = self._items.list_items(stage=Stage.PLANNED, limit=PROPOSAL_SCAN_LIMIT)
        return [
            (item, item.date)
            for item in planned
            if item.date is not None and self._planning.needs_proposal(item)
        ]

    def _propose(self, item: Item, day: dt.date, send: Callable[[Reply], None]) -> None:
        try:
            proposal = self._planning.propose_for(item.id)
        except PlanningRefused:
            return
        except Exception as error:
            logger.warning(PROPOSAL_FAILED_LOG, type(error).__name__)
            return
        self._send(item, proposal_reply(proposal, day), send)

    def _send(self, item: Item, reply: Reply, send: Callable[[Reply], None]) -> None:
        try:
            send(reply)
        except Exception as error:
            logger.warning(PROPOSAL_SEND_FAILED_LOG, type(error).__name__)
            self._withdraw(item)

    def _withdraw(self, item: Item) -> None:
        try:
            self._planning.withdraw(item.id)
        except Exception as error:
            logger.warning(PROPOSAL_WITHDRAW_FAILED_LOG, type(error).__name__)
