from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import partial
from zoneinfo import ZoneInfo

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.callbacks import KeepChoice, date_for, rating_for
from stash.capture.completion_replies import didnt_happen_reply, done_reply, kept_reply, rated_reply
from stash.capture.open_items import open_item_with_prefix
from stash.capture.ports import LifecycleActions
from stash.capture.replies import Reply, busy, changed, gone, refused
from stash.domain import Item, enum_member
from stash.lifecycle.errors import (
    ItemChanged,
    LifecycleRefused,
    StashBusy,
    UnknownItem,
    UnknownOutcome,
)
from stash.lifecycle.results import Completion, ItemHistory
from stash.store.port import Store

RATING_KIND = "rating"
DAY_KIND = "day"
DOUBLE_TAP_WINDOW = timedelta(seconds=60)


class CompletionButtons:
    def __init__(
        self,
        store: Store,
        lifecycle: LifecycleActions,
        callback_log: CallbackLog,
        clock: Callable[[], datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._store = store
        self._lifecycle = lifecycle
        self._log = callback_log
        self._clock = clock
        self._timezone = timezone

    def done(self, item_id: str) -> Reply:
        return answering(partial(self._completed, item_id), self._log)

    def progress_done(self, report_id: str, prefix: str | None) -> Reply:
        return answering(partial(self._progress_done, report_id, prefix or ""), self._log)

    def rate(self, outcome_id: str, argument: str | None) -> Reply:
        rating = rating_for(argument)
        if rating is None:
            self._log.invalid(Subject.OUTCOME, outcome_id, RATING_KIND, argument)
            return gone()
        return answering(partial(self._rated, outcome_id, rating), self._log)

    def keep(self, item_id: str, argument: str | None) -> Reply:
        choice = enum_member(KeepChoice, argument)
        if choice is None:
            self._log.invalid(Subject.ITEM, item_id, KeepChoice.__name__, argument)
            return gone()
        return answering(partial(self._kept, item_id, choice), self._log)

    def didnt_happen(self, item_id: str, argument: str | None) -> Reply:
        on = date_for(argument)
        if on is None:
            self._log.invalid(Subject.ITEM, item_id, DAY_KIND, argument)
            return gone()
        return answering(partial(self._didnt_happen, item_id, on), self._log)

    def _completed(self, item_id: str) -> Reply:
        history = self._lifecycle.history(item_id)
        double_tap = self._double_tap_of(history)
        if double_tap is not None:
            return done_reply(double_tap)
        return done_reply(
            self._lifecycle.complete(item_id, on=self._date_already_past(history.item))
        )

    def _progress_done(self, report_id: str, prefix: str) -> Reply:
        target = open_item_with_prefix(self._store, prefix)
        if self._store.get_item(report_id) is None or target is None or target.id == report_id:
            self._log.unknown(Subject.ITEM, report_id)
            return gone()
        reply = self._completed(target.id)
        self._store.delete_item_if_untouched(report_id)
        return reply

    def _date_already_past(self, item: Item) -> date | None:
        today = self._clock().astimezone(self._timezone).date()
        return item.date if item.date is not None and item.date <= today else None

    def _double_tap_of(self, history: ItemHistory) -> Completion | None:
        latest = history.latest_recorded
        if not history.item.is_done or latest is None:
            return None
        elapsed = self._clock() - latest.recorded_at
        if not timedelta(0) <= elapsed < DOUBLE_TAP_WINDOW:
            return None
        return Completion(history.item, latest, repeat=False)

    def _rated(self, outcome_id: str, rating: int) -> Reply:
        outcome = self._lifecycle.rate(outcome_id, rating)
        return rated_reply(self._lifecycle.history(outcome.item_id).item, rating)

    def _kept(self, item_id: str, choice: KeepChoice) -> Reply:
        self._lifecycle.keep(item_id, choice.kept)
        return kept_reply(self._lifecycle.history(item_id))

    def _didnt_happen(self, item_id: str, on: date) -> Reply:
        return didnt_happen_reply(self._lifecycle.didnt_happen(item_id, on))


def answering(build_reply: Callable[[], Reply], log: CallbackLog) -> Reply:
    try:
        return build_reply()
    except UnknownItem as error:
        log.unknown(Subject.ITEM, error.item_id)
        return gone()
    except ItemChanged as error:
        log.changed(Subject.ITEM, error.item_id)
        return changed()
    except StashBusy:
        log.busy()
        return busy()
    except UnknownOutcome as error:
        log.unknown(Subject.OUTCOME, error.outcome_id)
        return gone()
    except LifecycleRefused as error:
        return refused(str(error))
