from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from stash.domain import GROUPS_ONE_LEVEL_DEEP, Item, Outcome, frozen_strings
from stash.lifecycle.errors import LifecycleRefused, UnknownItem, UnknownOutcome
from stash.lifecycle.ports import LifecycleStore
from stash.lifecycle.results import Completion, ItemHistory
from stash.store.port import UnknownItemError

TAKEAWAYS_NOT_A_LIST = "takeaways must be a list of separate items, not one piece of text"


@contextmanager
def _refusing_what_the_domain_refuses() -> Iterator[None]:
    try:
        yield
    except ValueError as error:
        raise LifecycleRefused(str(error)) from error


@contextmanager
def _reporting_items_that_vanished() -> Iterator[None]:
    try:
        yield
    except UnknownItemError as error:
        raise UnknownItem(error.item_id) from error


class Lifecycle:
    def __init__(
        self,
        store: LifecycleStore,
        new_id: Callable[[], str],
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._store = store
        self._new_id = new_id
        self._clock = clock
        self._timezone = timezone

    def complete(
        self,
        item_id: str,
        *,
        rating: int | None = None,
        notes: str = "",
        takeaways: Sequence[str] = (),
        keep: bool | None = None,
        on: date | None = None,
    ) -> Completion:
        item = self._item(item_id)
        outcome_id = self._new_id()
        now = self._clock()
        repeat = item.is_done
        with _refusing_what_the_domain_refuses():
            outcome = Outcome(
                id=outcome_id,
                item_id=item.id,
                completed_on=on or self._today(now),
                rating=rating,
                notes=notes,
                takeaways=_takeaway_list(takeaways),
                recorded_at=now,
            )
            completed = _completed(item, repeat, keep, now)
        with _reporting_items_that_vanished():
            self._store.record_completion(completed, outcome)
        return Completion(completed, outcome, repeat=repeat)

    def keep(self, item_id: str, kept: bool) -> Item:
        item = self._item(item_id)
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = item.kept_as(kept, now)
        return self._saved(changed)

    def reopen(self, item_id: str) -> Item:
        item = self._item(item_id)
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = item.reopened(now)
        return self._saved(changed)

    def drop(self, item_id: str, reason: str | None) -> Item:
        item = self._item(item_id)
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = item.dropped(_unless_blank(reason), now)
        return self._saved(changed)

    def group(self, child_id: str, parent_id: str) -> Item:
        child = self._item(child_id)
        parent = self._item(parent_id)
        if self._store.children_of(child.id):
            raise LifecycleRefused(f"{GROUPS_ONE_LEVEL_DEEP}: {child.title} already holds items")
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = child.grouped_under(parent, now)
        return self._saved(changed)

    def ungroup(self, child_id: str) -> Item:
        child = self._item(child_id)
        now = self._clock()
        return self._saved(child.ungrouped(now))

    def annotate(self, outcome_id: str, notes: str, takeaways: Sequence[str]) -> Outcome:
        outcome = self._outcome(outcome_id)
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = outcome.with_notes(notes, _takeaway_list(takeaways), now)
        return self._saved_outcome(changed)

    def rate(self, outcome_id: str, rating: int) -> Outcome:
        outcome = self._outcome(outcome_id)
        now = self._clock()
        with _refusing_what_the_domain_refuses():
            changed = outcome.with_rating(rating, now)
        return self._saved_outcome(changed)

    def history(self, item_id: str) -> ItemHistory:
        item = self._item(item_id)
        outcomes = tuple(self._store.outcomes_for(item.id))
        return ItemHistory(item, outcomes, tuple(self._store.children_of(item.id)))

    def _saved_outcome(self, outcome: Outcome) -> Outcome:
        with _reporting_items_that_vanished():
            self._store.save_outcome(outcome)
        return outcome

    def _saved(self, item: Item) -> Item:
        with _reporting_items_that_vanished():
            self._store.save_item(item)
        return item

    def _item(self, item_id: str) -> Item:
        item = self._store.get_item(item_id)
        if item is None:
            raise UnknownItem(item_id)
        return item

    def _outcome(self, outcome_id: str) -> Outcome:
        outcome = self._store.get_outcome(outcome_id)
        if outcome is None:
            raise UnknownOutcome(outcome_id)
        return outcome

    def _today(self, now: datetime) -> date:
        return now.astimezone(self._timezone).date()


def _takeaway_list(takeaways: Sequence[str]) -> tuple[str, ...]:
    if isinstance(takeaways, str):
        raise LifecycleRefused(TAKEAWAYS_NOT_A_LIST)
    return frozen_strings("takeaways", takeaways)


def _completed(item: Item, repeat: bool, keep: bool | None, now: datetime) -> Item:
    done = item if repeat else item.completed(now)
    return done if keep is None else done.kept_as(keep, now)


def _unless_blank(reason: str | None) -> str | None:
    return reason if reason is not None and reason.strip() else None
