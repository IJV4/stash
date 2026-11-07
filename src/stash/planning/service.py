import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from stash.domain import Item, Stage, Step
from stash.planning.errors import PlanningBusy, PlanningRefused, UnknownItem, UnknownStep
from stash.planning.ports import PlanningStore, ProposalDeclines, StepProposals
from stash.planning.results import Proposal, ProposedStep
from stash.store.port import StoreBusyError, UnknownItemError

NOT_PROPOSABLE = "only a planned item with a date and no steps can get proposed steps"


@contextmanager
def _refusing_what_the_domain_refuses() -> Iterator[None]:
    try:
        yield
    except ValueError as error:
        raise PlanningRefused(str(error)) from error


@contextmanager
def _translating_store_errors() -> Iterator[None]:
    try:
        yield
    except UnknownItemError as error:
        raise UnknownItem(error.item_id) from error
    except StoreBusyError as error:
        raise PlanningBusy from error


def _any_unconfirmed(steps: Sequence[Step]) -> bool:
    return any(not step.confirmed for step in steps)


class Planning:
    def __init__(
        self,
        store: PlanningStore,
        proposer: StepProposals,
        declines: ProposalDeclines,
        new_id: Callable[[], str],
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._store = store
        self._proposer = proposer
        self._declines = declines
        self._new_id = new_id
        self._clock = clock
        self._timezone = timezone
        self._lock = threading.Lock()

    def needs_proposal(self, item: Item) -> bool:
        return (
            item.stage is Stage.PLANNED
            and item.date is not None
            and item.date >= self._today()
            and not self._store.steps_for(item.id)
            and not self._declines.is_declined(item)
        )

    def propose_for(self, item_id: str) -> Proposal:
        item = self._item(item_id)
        if not self.needs_proposal(item):
            raise PlanningRefused(NOT_PROPOSABLE)
        proposals = self._proposer.propose(item)
        with self._lock, _translating_store_errors():
            current = self._item(item_id)
            if current.date != item.date or not self.needs_proposal(current):
                raise PlanningRefused(NOT_PROPOSABLE)
            steps = self._as_unconfirmed_steps(item_id, proposals)
            if steps:
                self._store.save_steps(item_id, steps)
            else:
                self._declines.record(current)
        return Proposal(current, steps)

    def confirm_all(self, item_id: str) -> tuple[Step, ...]:
        with self._locked_item(item_id):
            steps = self._store.steps_for(item_id)
            confirmed = tuple(step.confirmed_now() for step in steps)
            if _any_unconfirmed(steps):
                self._store.save_steps(item_id, confirmed)
        return confirmed

    def discard(self, item_id: str) -> None:
        with self._locked_item(item_id):
            self._declines.record(self._item(item_id))
            self._drop_unconfirmed_steps(item_id)

    def withdraw(self, item_id: str) -> None:
        with self._locked_item(item_id):
            self._drop_unconfirmed_steps(item_id)

    def add_step(
        self,
        item_id: str,
        text: str,
        *,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step:
        with self._locked_item(item_id):
            positions = [step.position for step in self._store.steps_for(item_id)]
            with _refusing_what_the_domain_refuses():
                step = Step(
                    id=self._new_id(),
                    item_id=item_id,
                    text=text,
                    lead_days=lead_days,
                    due_on=due_on,
                    confirmed=True,
                    done=False,
                    position=1 + max(positions, default=-1),
                    created_at=self._clock(),
                )
            self._store.save_step(step)
        return step

    def edit_step(
        self,
        step_id: str,
        *,
        text: str | None = None,
        lead_days: int | None = None,
        due_on: date | None = None,
    ) -> Step:
        with self._lock, _translating_store_errors():
            current = self._step(step_id)
            with _refusing_what_the_domain_refuses():
                edited = current.edited(text=text, lead_days=lead_days, due_on=due_on)
            self._store.save_step(edited)
        return edited

    def complete_step(self, step_id: str) -> Step:
        with self._lock, _translating_store_errors():
            done = self._step(step_id).confirmed_now().marked_done()
            self._store.save_step(done)
        return done

    @contextmanager
    def _locked_item(self, item_id: str) -> Iterator[None]:
        self._item(item_id)
        with self._lock, _translating_store_errors():
            yield

    def _drop_unconfirmed_steps(self, item_id: str) -> None:
        steps = self._store.steps_for(item_id)
        if _any_unconfirmed(steps):
            self._store.save_steps(item_id, [step for step in steps if step.confirmed])

    def _as_unconfirmed_steps(
        self, item_id: str, proposals: Sequence[ProposedStep]
    ) -> tuple[Step, ...]:
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            return tuple(
                proposal.as_step(self._new_id(), item_id, position, now)
                for position, proposal in enumerate(proposals)
            )

    def _today(self) -> date:
        return self._clock().astimezone(self._timezone).date()

    def _item(self, item_id: str) -> Item:
        item = self._store.get_item(item_id)
        if item is None:
            raise UnknownItem(item_id)
        return item

    def _step(self, step_id: str) -> Step:
        step = self._store.get_step(step_id)
        if step is None:
            raise UnknownStep(step_id)
        return step
