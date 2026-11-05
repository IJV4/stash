from collections.abc import Callable
from datetime import datetime, timedelta
from functools import partial

from stash.capture.callback_log import CallbackLog, Subject
from stash.capture.callbacks import KeepChoice, rating_for
from stash.capture.completion_replies import done_reply, kept_reply, rated_reply
from stash.capture.ports import FixStore, LifecycleActions
from stash.capture.replies import Reply, gone, refused
from stash.domain import enum_member
from stash.lifecycle.errors import LifecycleRefused, UnknownItem, UnknownOutcome
from stash.lifecycle.results import Completion, ItemHistory

RATING_KIND = "rating"
DOUBLE_TAP_WINDOW = timedelta(seconds=60)


class CompletionButtons:
    def __init__(
        self,
        store: FixStore,
        lifecycle: LifecycleActions,
        callback_log: CallbackLog,
        clock: Callable[[], datetime],
    ) -> None:
        self._store = store
        self._lifecycle = lifecycle
        self._log = callback_log
        self._clock = clock

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

    def _completed(self, item_id: str) -> Reply:
        double_tap = self._double_tap_of(self._lifecycle.history(item_id))
        if double_tap is not None:
            return done_reply(double_tap)
        return done_reply(self._lifecycle.complete(item_id))

    def _double_tap_of(self, history: ItemHistory) -> Completion | None:
        if not history.item.is_done or not history.outcomes:
            return None
        latest = max(history.outcomes, key=lambda outcome: outcome.recorded_at)
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
        return kept_reply(self._lifecycle.keep(item_id, choice.kept))

    def _answering(self, build_reply: Callable[[], Reply]) -> Reply:
        try:
            return build_reply()
        except UnknownItem as error:
            self._log.unknown(Subject.ITEM, error.item_id)
            return gone()
        except UnknownOutcome as error:
            self._log.unknown(Subject.OUTCOME, error.outcome_id)
            return gone()
        except LifecycleRefused as error:
            return refused(str(error))
