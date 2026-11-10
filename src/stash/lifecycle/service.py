from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from stash.domain import Item, ItemType, Outcome, Stage, frozen_strings
from stash.lifecycle._guards import (
    refusing_what_the_domain_refuses,
    refusing_what_the_store_refuses_for_a_group,
    translating_store_errors,
)
from stash.lifecycle.errors import ItemChanged, LifecycleRefused, UnknownItem, UnknownOutcome
from stash.lifecycle.query import DEFAULT_LIBRARY_QUERY, LibraryQuery
from stash.lifecycle.results import Completion, ItemHistory, LibraryEntry
from stash.store.port import Store

REASON_ONLY_FOR_DROPPING = "a reason is only for dropping an item"
TAKEAWAYS_NOT_A_LIST = "takeaways must be a list of separate items, not one piece of text"
NOTHING_TO_ANNOTATE = "give notes, takeaways or a rating"

COMPLETED_AFTER_TOMORROW = "completed_on {on} is after tomorrow"
COMPLETION_DATE_SLACK = timedelta(days=1)


class Lifecycle:
    def __init__(
        self,
        store: Store,
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
        with self._store.writing():
            item = self._item(item_id)
            outcome_id = self._new_id()
            now = self._clock()
            self._refuse_a_date_after_tomorrow(on, now)
            repeat = item.is_done
            with refusing_what_the_domain_refuses():
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
            with translating_store_errors():
                self._store.record_completion(completed, outcome)
        return Completion(completed, outcome, repeat=repeat)

    def keep(self, item_id: str, kept: bool) -> Item:
        return self._changed(item_id, lambda item, now: item.kept_as(kept, now))

    def drop(self, item_id: str, reason: str | None) -> Item:
        return self._changed(item_id, lambda item, now: item.dropped(_unless_blank(reason), now))

    def retype(self, item_id: str, item_type: ItemType) -> Item:
        return self._changed(item_id, lambda item, now: item.retyped(item_type, now))

    def didnt_happen(self, item_id: str, on: date) -> Item:
        with self._store.writing():
            item = self._item(item_id)
            if not item.is_planned:
                return item
            if item.date != on:
                raise ItemChanged(item_id)
            return self._saved(item.unplanned(self._clock()))

    def reschedule(self, item_id: str, on: date | None) -> Item:
        return self._changed(item_id, lambda item, now: item.rescheduled(on, now))

    def set_stage(self, item_id: str, stage: Stage, reason: str | None = None) -> Item:
        if stage is Stage.DROPPED:
            return self.drop(item_id, reason)
        if _unless_blank(reason) is not None:
            raise LifecycleRefused(REASON_ONLY_FOR_DROPPING)
        return self._changed(item_id, lambda item, now: item.relocated_to(stage, now))

    def group(self, child_id: str, parent_id: str) -> Item:
        with self._store.writing():
            child = self._item(child_id)
            parent = self._item(parent_id)
            now = self._clock()
            with refusing_what_the_domain_refuses():
                changed = child.grouped_under(parent, now)
            with translating_store_errors(), refusing_what_the_store_refuses_for_a_group(child):
                self._store.group_item(changed)
        return changed

    def ungroup(self, child_id: str) -> Item:
        return self._changed(child_id, lambda child, now: child.ungrouped(now))

    def annotate(
        self,
        outcome_id: str,
        *,
        notes: str | None = None,
        takeaways: Sequence[str] | None = None,
        rating: int | None = None,
    ) -> Outcome:
        if notes is None and takeaways is None and rating is None:
            raise LifecycleRefused(NOTHING_TO_ANNOTATE)
        kept_or_replaced = None if takeaways is None else _takeaway_list(takeaways)

        def annotated(outcome: Outcome, now: datetime) -> Outcome:
            changed = outcome.with_notes(notes, kept_or_replaced, now)
            return changed if rating is None else changed.with_rating(rating, now)

        return self._changed_outcome(outcome_id, annotated)

    def rate(self, outcome_id: str, rating: int) -> Outcome:
        return self._changed_outcome(
            outcome_id, lambda outcome, now: outcome.with_rating(rating, now)
        )

    def history(self, item_id: str) -> ItemHistory:
        item = self._item(item_id)
        outcomes = tuple(self._store.outcomes_for(item.id))
        return ItemHistory(item, outcomes, tuple(self._store.children_of(item.id)))

    def library(self, query: LibraryQuery = DEFAULT_LIBRARY_QUERY) -> tuple[LibraryEntry, ...]:
        items = self._store.library(query.item_type, query.limit)
        return tuple(LibraryEntry(item, self._last_finished(item)) for item in items)

    def _last_finished(self, item: Item) -> Outcome | None:
        outcomes = self._store.outcomes_for(item.id)
        return outcomes[-1] if outcomes else None

    def _changed(self, item_id: str, change: Callable[[Item, datetime], Item]) -> Item:
        with self._store.writing():
            item = self._item(item_id)
            now = self._clock()
            with refusing_what_the_domain_refuses():
                changed = change(item, now)
            return self._saved(changed)

    def _changed_outcome(
        self, outcome_id: str, change: Callable[[Outcome, datetime], Outcome]
    ) -> Outcome:
        with self._store.writing():
            outcome = self._outcome(outcome_id)
            now = self._clock()
            with refusing_what_the_domain_refuses():
                changed = change(outcome, now)
            with translating_store_errors():
                self._store.save_outcome(changed)
        return changed

    def _saved(self, changed: Item) -> Item:
        with translating_store_errors():
            self._store.update_item(changed)
        return changed

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

    def _refuse_a_date_after_tomorrow(self, on: date | None, now: datetime) -> None:
        if on is not None and on > self._today(now) + COMPLETION_DATE_SLACK:
            raise LifecycleRefused(COMPLETED_AFTER_TOMORROW.format(on=on))

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
