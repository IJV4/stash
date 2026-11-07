from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import partial
from zoneinfo import ZoneInfo

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.callbacks import KeepChoice, date_for, rating_for
from stash.capture.completion_replies import didnt_happen_reply, done_reply, kept_reply, rated_reply
from stash.capture.ports import FixStore, LifecycleActions
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

RATING_KIND = "rating"
DAY_KIND = "day"
DOUBLE_TAP_WINDOW = timedelta(seconds=60)


class CompletionButtons:
    def __init__(
        self,
        store: FixStore,
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
        return self._answering(partial(self._completed, item_id))

    def rate(self, outcome_id: str, argument: str | None) -> Reply:
        rating = rating_for(argument)
        if rating is None:
            self._log.invalid(Subject.OUTCOME, outcome_id, RATING_KIND, argument)
            return gone()
        return self._answering(partial(self._rated, outcome_id, rating))

    def keep(self, item_id: str, argument: str | None) -> Reply:
        choice = enum_member(KeepChoice, argument)
        if choice is None:
            self._log.invalid(Subject.ITEM, item_id, KeepChoice.__name__, argument)
            return gone()
        return self._answering(partial(self._kept, item_id, choice))

    def didnt_happen(self, item_id: str, argument: str | None) -> Reply:
        on = date_for(argument)
        if on is None:
            self._log.invalid(Subject.ITEM, item_id, DAY_KIND, argument)
            return gone()
        return self._answering(partial(self._didnt_happen, item_id, on))

    def _completed(self, item_id: str) -> Reply:
        history = self._lifecycle.history(item_id)
        double_tap = self._double_tap_of(history)
        if double_tap is not None:
            return done_reply(double_tap)
        return done_reply(
            self._lifecycle.complete(item_id, on=self._date_already_past(history.item))
        )

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
        item = self._store.get_item(outcome.item_id)
        if item is None:
            self._log.unknown(Subject.ITEM, outcome.item_id)
            return gone()
        return rated_reply(item, rating)

    def _kept(self, item_id: str, choice: KeepChoice) -> Reply:
        self._lifecycle.keep(item_id, choice.kept)
        return kept_reply(self._lifecycle.history(item_id))

    def _didnt_happen(self, item_id: str, on: date) -> Reply:
        return didnt_happen_reply(self._lifecycle.didnt_happen(item_id, on))

    def _answering(self, build_reply: Callable[[], Reply]) -> Reply:
        try:
            return build_reply()
        except UnknownItem as error:
            self._log.unknown(Subject.ITEM, error.item_id)
            return gone()
        except ItemChanged as error:
            self._log.changed(Subject.ITEM, error.item_id)
            return changed()
        except StashBusy:
            self._log.busy()
            return busy()
        except UnknownOutcome as error:
            self._log.unknown(Subject.OUTCOME, error.outcome_id)
            return gone()
        except LifecycleRefused as error:
            return refused(str(error))
